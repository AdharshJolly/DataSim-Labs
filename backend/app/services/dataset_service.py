import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.models.dataset import Attribute, Dataset, DatasetVersion
from app.schemas.dataset import AttributeConfig


class DatasetService:
    @staticmethod
    def create_dataset(
        db: Session,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Dataset:
        dataset = Dataset(user_id=user_id, name=name, description=description)
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return dataset

    @staticmethod
    def create_dataset_version(
        db: Session,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        attributes: list[AttributeConfig],
    ) -> DatasetVersion:
        dataset = db.scalar(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user_id)
        )
        if dataset is None:
            raise ValueError("Dataset not found")

        next_version_number = db.scalar(
            select(func.coalesce(func.max(DatasetVersion.version_number), 0) + 1).where(
                DatasetVersion.dataset_id == dataset_id
            )
        )

        config_json = {
            "attributes": [
                attribute.model_dump(mode="json") for attribute in attributes
            ],
        }

        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number=int(next_version_number or 1),
            config_json=config_json,
        )
        db.add(version)
        db.flush()

        for index, attribute in enumerate(attributes):
            db.add(
                Attribute(
                    dataset_version_id=version.id,
                    name=attribute.name,
                    data_type=attribute.type,
                    description=attribute.description,
                    constraints_json=attribute.constraints,
                    distribution=attribute.distribution,
                    null_percentage=attribute.null_percentage,
                    order_index=index,
                )
            )

        dataset.latest_version_id = version.id
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def generate_preview(
        db: Session,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a 10-row preview from persisted attribute configuration."""
        version = db.scalar(
            select(DatasetVersion)
            .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
            .where(DatasetVersion.id == dataset_version_id, Dataset.user_id == user_id)
        )
        if version is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, dataset_version_id)
        generator = DatasetGenerator(seed=seed)
        return generator.generate_preview(attributes=attributes)

    @staticmethod
    def generate_dataset_files(
        db: Session,
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
        dataset = db.scalar(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user_id)
        )
        if dataset is None:
            raise ValueError("Dataset not found")

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        owned_version = db.scalar(
            select(DatasetVersion).where(
                DatasetVersion.id == target_version_id,
                DatasetVersion.dataset_id == dataset.id,
            )
        )
        if owned_version is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, target_version_id)
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        DatasetService.cleanup_old_artifacts(
            output_root=output_root,
            max_age_hours=retention_hours,
        )
        generator = DatasetGenerator(seed=seed)
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
                    "file_path": str(path),
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
    def list_datasets(db: Session, user_id: uuid.UUID) -> list[Dataset]:
        """List all datasets owned by a user."""
        return db.scalars(
            select(Dataset)
            .where(Dataset.user_id == user_id)
            .order_by(Dataset.created_at.desc())
        ).all()

    @staticmethod
    def get_dataset(db: Session, user_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset:
        """Get one dataset if owned by the user."""
        dataset = db.scalar(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user_id)
        )
        if dataset is None:
            raise ValueError("Dataset not found")
        return dataset

    @staticmethod
    def get_dataset_versions(
        db: Session,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> list[DatasetVersion]:
        """Get all versions for one dataset if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        return db.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset.id)
            .order_by(DatasetVersion.version_number.desc())
        ).all()

    @staticmethod
    def delete_dataset(db: Session, user_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        """Delete dataset and all versions/attributes if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        db.delete(dataset)
        db.commit()

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
        db: Session, dataset_version_id: uuid.UUID
    ) -> list[AttributeSpec]:
        """Load and normalize version attributes for generation engine use."""
        rows = db.scalars(
            select(Attribute)
            .where(Attribute.dataset_version_id == dataset_version_id)
            .order_by(Attribute.order_index.asc())
        ).all()

        return [
            AttributeSpec(
                name=row.name,
                data_type=row.data_type.value,
                constraints=row.constraints_json or {},
                distribution=row.distribution.value,
                null_percentage=row.null_percentage,
            )
            for row in rows
        ]
