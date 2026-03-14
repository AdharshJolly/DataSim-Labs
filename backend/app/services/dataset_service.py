import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
