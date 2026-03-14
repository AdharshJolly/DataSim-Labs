import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.models.dataset import Attribute, Dataset, DatasetVersion
from app.schemas.dataset import AttributeConfig


class DatasetService:
    @staticmethod
    def create_dataset(db: Session, name: str, description: str | None) -> Dataset:
        dataset = Dataset(name=name, description=description)
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return dataset

    @staticmethod
    def create_dataset_version(
        db: Session,
        dataset_id: uuid.UUID,
        attributes: list[AttributeConfig],
    ) -> DatasetVersion:
        dataset = db.get(Dataset, dataset_id)
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
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a 10-row preview from persisted attribute configuration."""
        version = db.get(DatasetVersion, dataset_version_id)
        if version is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, dataset_version_id)
        generator = DatasetGenerator(seed=seed)
        return generator.generate_preview(attributes=attributes)

    @staticmethod
    def generate_dataset_files(
        db: Session,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        output_root: Path,
        chunk_size: int,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate and export full datasets for a dataset's latest version."""
        dataset = db.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found")

        if dataset.latest_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        attributes = DatasetService._load_version_attributes(
            db, dataset.latest_version_id
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
        dataset_id: uuid.UUID, output_root: Path
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
