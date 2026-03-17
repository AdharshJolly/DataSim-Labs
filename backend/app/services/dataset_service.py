import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pymongo import DESCENDING
from pymongo.database import Database

from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.models.dataset import Attribute, Dataset, DatasetStatus, DatasetVersion
from app.schemas.dataset import AttributeConfig


class DatasetService:
    @staticmethod
    def create_dataset(
        db: Database,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Dataset:
        dataset = Dataset.new(user_id=user_id, name=name, description=description)
        db["datasets"].insert_one(dataset.to_document())
        return dataset

    @staticmethod
    def create_dataset_version(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        attributes: list[AttributeConfig],
        seed: int | None = None,
    ) -> DatasetVersion:
        attr_names = [attr.name for attr in attributes]
        if len(attr_names) != len(set(attr_names)):
            raise ValueError("Attribute names must be unique within a version")

        dataset_doc = db["datasets"].find_one(
            {"_id": str(dataset_id), "user_id": str(user_id)}
        )
        if dataset_doc is None:
            raise ValueError("Dataset not found")
        dataset = Dataset.from_document(dataset_doc)

        latest_version = db["dataset_versions"].find_one(
            {"dataset_id": str(dataset_id)},
            sort=[("version_number", DESCENDING)],
        )
        next_version_number = (
            int(latest_version["version_number"]) + 1 if latest_version else 1
        )

        config_json = {
            "attributes": [
                attribute.model_dump(mode="json") for attribute in attributes
            ],
            "seed": seed,
        }

        version = DatasetVersion.new(
            dataset_id=dataset_id,
            version_number=next_version_number,
            config_json=config_json,
            seed=seed,
        )
        db["dataset_versions"].insert_one(version.to_document())

        attribute_documents: list[dict[str, Any]] = []
        for index, attribute in enumerate(attributes):
            attribute_documents.append(
                Attribute.new(
                    dataset_version_id=version.id,
                    name=attribute.name,
                    data_type=attribute.type,
                    description=attribute.description,
                    constraints_json=attribute.constraints,
                    distribution=attribute.distribution,
                    null_percentage=attribute.null_percentage,
                    order_index=index,
                ).to_document()
            )

        if attribute_documents:
            db["attributes"].insert_many(attribute_documents)

        now = datetime.now(timezone.utc)
        db["datasets"].update_one(
            {"_id": str(dataset.id)},
            {
                "$set": {
                    "latest_version_id": str(version.id),
                    "status": DatasetStatus.active.value,
                    "updated_at": now,
                }
            },
        )
        return version

    @staticmethod
    def generate_preview(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a 10-row preview from persisted attribute configuration."""
        version_doc = db["dataset_versions"].find_one({"_id": str(dataset_version_id)})
        if version_doc is None:
            raise ValueError("Dataset version not found")
        version = DatasetVersion.from_document(version_doc)

        dataset_doc = db["datasets"].find_one(
            {"_id": str(version.dataset_id), "user_id": str(user_id)}
        )
        if dataset_doc is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, dataset_version_id)
        generator_seed = seed if seed is not None else version.seed
        generator = DatasetGenerator(seed=generator_seed)
        return generator.generate_preview(attributes=attributes)

    @staticmethod
    def generate_dataset_files(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        output_root: Path,
        chunk_size: int,
        seed: int | None = None,
        dataset_version_id: uuid.UUID | None = None,
        retention_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Generate and export full datasets for a dataset's latest version."""
        dataset_doc = db["datasets"].find_one(
            {"_id": str(dataset_id), "user_id": str(user_id)}
        )
        if dataset_doc is None:
            raise ValueError("Dataset not found")
        dataset = Dataset.from_document(dataset_doc)

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        version_doc = db["dataset_versions"].find_one(
            {"_id": str(target_version_id), "dataset_id": str(dataset.id)}
        )
        if version_doc is None:
            raise ValueError("Dataset version not found")
        owned_version = DatasetVersion.from_document(version_doc)

        attributes = DatasetService._load_version_attributes(db, target_version_id)
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        DatasetService.cleanup_old_artifacts(
            output_root=output_root,
            max_age_hours=retention_hours,
        )
        generator_seed = seed if seed is not None else owned_version.seed
        generator = DatasetGenerator(seed=generator_seed)
        return generator.export_dataset_files(
            dataset_id=dataset_id,
            attributes=attributes,
            row_count=row_count,
            formats=formats,
            output_root=output_root,
            chunk_size=chunk_size,
        )

    @staticmethod
    def list_generated_files(
        dataset_id: uuid.UUID,
        output_root: Path,
    ) -> list[dict[str, Any]]:
        """List generated files available for a dataset on disk."""
        dataset_dir = output_root / str(dataset_id)
        if not dataset_dir.exists():
            return []

        result: list[dict[str, Any]] = []
        for path in sorted(dataset_dir.glob("*")):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            if suffix == ".csv":
                export_format = "csv"
            elif suffix == ".json":
                export_format = "json"
            elif suffix == ".xlsx":
                export_format = "excel"
            else:
                continue

            result.append(
                {
                    "format": export_format,
                    "file_name": path.name,
                    "size_bytes": path.stat().st_size,
                }
            )

        return result

    @staticmethod
    def resolve_generated_file(
        dataset_id: uuid.UUID,
        output_root: Path,
        export_format: str,
    ) -> Path | None:
        """Resolve one generated file for download by dataset and format."""
        suffix_map = {
            "csv": ".csv",
            "json": ".json",
            "excel": ".xlsx",
        }
        suffix = suffix_map.get(export_format.lower())
        if suffix is None:
            return None

        dataset_dir = output_root / str(dataset_id)
        if not dataset_dir.exists():
            return None

        candidates = sorted(
            dataset_dir.glob(f"*{suffix}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    @staticmethod
    def list_datasets(db: Database, user_id: uuid.UUID) -> list[Dataset]:
        """List all datasets owned by a user."""
        rows = (
            db["datasets"]
            .find({"user_id": str(user_id)})
            .sort("created_at", DESCENDING)
        )
        return [Dataset.from_document(row) for row in rows]

    @staticmethod
    def get_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset:
        """Get one dataset if owned by the user."""
        row = db["datasets"].find_one({"_id": str(dataset_id), "user_id": str(user_id)})
        if row is None:
            raise ValueError("Dataset not found")
        return Dataset.from_document(row)

    @staticmethod
    def get_dataset_versions(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> list[DatasetVersion]:
        """Get all versions for one dataset if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        rows = (
            db["dataset_versions"]
            .find({"dataset_id": str(dataset.id)})
            .sort("version_number", DESCENDING)
        )
        return [DatasetVersion.from_document(row) for row in rows]

    @staticmethod
    def delete_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        """Delete dataset and all versions/attributes if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        versions = db["dataset_versions"].find({"dataset_id": str(dataset.id)})
        version_ids = [row["_id"] for row in versions]
        if version_ids:
            db["attributes"].delete_many({"dataset_version_id": {"$in": version_ids}})
        db["dataset_versions"].delete_many({"dataset_id": str(dataset.id)})
        db["datasets"].delete_one({"_id": str(dataset.id)})

    @staticmethod
    def update_dataset_status(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        status: DatasetStatus,
    ) -> Dataset:
        """Update dataset status if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )
        now = datetime.now(timezone.utc)
        db["datasets"].update_one(
            {"_id": str(dataset.id)},
            {"$set": {"status": status.value, "updated_at": now}},
        )
        dataset.status = status
        dataset.updated_at = now
        return dataset

    @staticmethod
    def cleanup_old_artifacts(output_root: Path, max_age_hours: int) -> None:
        """Delete generated files older than retention window."""
        if not output_root.exists():
            return

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        for dataset_dir in output_root.glob("*"):
            if not dataset_dir.is_dir():
                continue
            for file_path in dataset_dir.glob("*"):
                if not file_path.is_file():
                    continue
                modified_at = datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=timezone.utc
                )
                if modified_at < cutoff:
                    file_path.unlink(missing_ok=True)

    @staticmethod
    def _load_version_attributes(
        db: Database, dataset_version_id: uuid.UUID
    ) -> list[AttributeSpec]:
        """Load and normalize version attributes for generation engine use."""
        rows = (
            db["attributes"]
            .find({"dataset_version_id": str(dataset_version_id)})
            .sort("order_index", 1)
        )
        attributes = [Attribute.from_document(row) for row in rows]

        return [
            AttributeSpec(
                name=row.name,
                data_type=row.data_type.value,
                constraints=row.constraints_json or {},
                distribution=row.distribution.value,
                null_percentage=row.null_percentage,
            )
            for row in attributes
        ]
