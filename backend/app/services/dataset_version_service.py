"""Service functions centered on DatasetVersion read/write operations."""

from __future__ import annotations

import uuid
from typing import Any

from pymongo.database import Database

from app.engine.dataset_generator import AttributeSpec
from app.models.dataset import DatasetVersion
from app.schemas.dataset import AttributeConfig
from app.services.dataset_repository import DatasetRepository
from app.services.orchestration.generation_orchestrator import GenerationOrchestrator


class DatasetVersionService:
    """Dataset version operations including creation and semantic rule updates."""

    @staticmethod
    def create_dataset_version(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        attributes: list[AttributeConfig],
        seed: int | None = None,
        correlations: list[dict[str, Any]] | None = None,
    ) -> DatasetVersion:
        return GenerationOrchestrator.create_dataset_version(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            attributes=attributes,
            seed=seed,
            correlations=correlations,
        )

    @staticmethod
    def get_dataset_versions(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> list[DatasetVersion]:
        return DatasetRepository.get_dataset_versions(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )

    @staticmethod
    def get_dataset_version_for_user(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
    ) -> DatasetVersion:
        return DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
        )

    @staticmethod
    def update_dataset_version_semantic_rules(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        semantic_rules: list[dict[str, Any]],
        conflict_policy: str | None = None,
    ) -> DatasetVersion:
        return DatasetRepository.update_dataset_version_semantic_rules(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
            semantic_rules=semantic_rules,
            conflict_policy=conflict_policy,
        )

    @staticmethod
    def get_dataset_version_attribute_names(
        db: Database,
        dataset_version_id: uuid.UUID,
    ) -> list[str]:
        attributes = DatasetRepository.load_version_attributes(
            db=db,
            dataset_version_id=dataset_version_id,
        )
        return [attribute.name for attribute in attributes]
