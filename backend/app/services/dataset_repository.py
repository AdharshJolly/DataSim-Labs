"""
dataset_repository.py

Data access layer for datasets and versions. Handles all MongoDB operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import DESCENDING
from pymongo.database import Database

from app.models.dataset import Attribute, Dataset, DatasetStatus, DatasetVersion
from app.schemas.dataset import AttributeConfig


class DatasetRepository:
    """Database operations for datasets and versions."""

    @staticmethod
    def create_dataset(
        db: Database,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Dataset:
        """Create a new dataset."""
        dataset = Dataset.new(user_id=user_id, name=name, description=description)
        db["datasets"].insert_one(dataset.to_document())
        return dataset

    @staticmethod
    def get_dataset(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> Dataset:
        """Get one dataset if owned by the user."""
        row = db["datasets"].find_one({"_id": str(dataset_id), "user_id": str(user_id)})
        if row is None:
            raise ValueError("Dataset not found")
        return Dataset.from_document(row)

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
    def delete_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        """Delete dataset and all versions/attributes if owned by user."""
        dataset = DatasetRepository.get_dataset(
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
        dataset = DatasetRepository.get_dataset(
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
    def create_dataset_version(
        db: Database,
        dataset: Dataset,
        attributes: list[AttributeConfig],
        config_json: dict[str, Any],
        seed: int | None = None,
    ) -> DatasetVersion:
        """Create a new dataset version with attributes."""
        latest_version = db["dataset_versions"].find_one(
            {"dataset_id": str(dataset.id)},
            sort=[("version_number", DESCENDING)],
        )
        next_version_number = (
            int(latest_version["version_number"]) + 1 if latest_version else 1
        )

        version = DatasetVersion.new(
            dataset_id=dataset.id,
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

        # Update dataset with new version reference
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
    def get_dataset_version(
        db: Database,
        dataset_version_id: uuid.UUID,
    ) -> DatasetVersion:
        """Get one dataset version."""
        version_doc = db["dataset_versions"].find_one({"_id": str(dataset_version_id)})
        if version_doc is None:
            raise ValueError("Dataset version not found")
        return DatasetVersion.from_document(version_doc)

    @staticmethod
    def get_dataset_versions(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> list[DatasetVersion]:
        """Get all versions for one dataset if owned by user."""
        dataset = DatasetRepository.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        rows = (
            db["dataset_versions"]
            .find({"dataset_id": str(dataset.id)})
            .sort("version_number", DESCENDING)
        )
        return [DatasetVersion.from_document(row) for row in rows]

    @staticmethod
    def get_dataset_version_for_user(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
    ) -> DatasetVersion:
        """Get one dataset version and verify it belongs to the user."""
        version = DatasetRepository.get_dataset_version(
            db=db,
            dataset_version_id=dataset_version_id,
        )
        DatasetRepository.get_dataset(
            db=db,
            user_id=user_id,
            dataset_id=version.dataset_id,
        )
        return version

    @staticmethod
    def update_dataset_version_semantic_rules(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        semantic_rules: list[dict[str, Any]],
        conflict_policy: str | None = None,
    ) -> DatasetVersion:
        """Update semantic rules in dataset version config_json."""
        version = DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
        )

        config_json = dict(version.config_json or {})
        config_json["semantic_rules"] = semantic_rules
        if conflict_policy:
            semantic_rule_settings = dict(
                config_json.get("semantic_rule_settings") or {}
            )
            semantic_rule_settings["conflict_policy"] = conflict_policy
            config_json["semantic_rule_settings"] = semantic_rule_settings

        db["dataset_versions"].update_one(
            {"_id": str(dataset_version_id)},
            {"$set": {"config_json": config_json}},
        )

        return DatasetVersion(
            id=version.id,
            dataset_id=version.dataset_id,
            version_number=version.version_number,
            config_json=config_json,
            seed=version.seed,
            created_at=version.created_at,
        )

    @staticmethod
    def load_version_attributes(
        db: Database,
        dataset_version_id: uuid.UUID,
    ) -> list[Attribute]:
        """Load all attributes for a version."""
        rows = (
            db["attributes"]
            .find({"dataset_version_id": str(dataset_version_id)})
            .sort("order_index", 1)
        )
        return [Attribute.from_document(row) for row in rows]
