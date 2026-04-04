"""Read-only dataset and generation query operations."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pymongo.database import Database

from app.models.dataset import Dataset, DatasetStatus
from app.services.dataset_repository import DatasetRepository
from app.services.job_manager import JobManager
from app.services.orchestration.generation_orchestrator import GenerationOrchestrator


class DatasetQueryService:
    """Read-only operations for datasets, jobs, and generated artifacts."""

    @staticmethod
    def get_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset:
        return DatasetRepository.get_dataset(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )

    @staticmethod
    def list_datasets(db: Database, user_id: uuid.UUID) -> list[Dataset]:
        return DatasetRepository.list_datasets(db=db, user_id=user_id)

    @staticmethod
    def list_generation_jobs(
        db: Database,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return JobManager.list_generation_jobs(db=db, user_id=user_id, limit=limit)

    @staticmethod
    def get_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        return JobManager.get_generation_job(db=db, user_id=user_id, job_id=job_id)

    @staticmethod
    def list_active_generation_job_dataset_ids(
        db: Database,
        user_id: uuid.UUID,
    ) -> set[str]:
        return JobManager.list_active_generation_job_dataset_ids(db=db, user_id=user_id)

    @staticmethod
    def serialize_generation_job(job: dict[str, Any]) -> dict[str, Any]:
        return JobManager.serialize_generation_job(job)

    @staticmethod
    def list_generated_files(
        dataset_id: uuid.UUID,
        output_root: Path,
    ) -> list[dict[str, Any]]:
        return GenerationOrchestrator.list_generated_files(
            dataset_id=dataset_id,
            output_root=output_root,
        )

    @staticmethod
    def resolve_generated_file(
        dataset_id: uuid.UUID,
        output_root: Path,
        export_format: str,
    ) -> Path | None:
        return GenerationOrchestrator.resolve_generated_file(
            dataset_id=dataset_id,
            output_root=output_root,
            export_format=export_format,
        )

    @staticmethod
    def resolve_effective_dataset_status(
        dataset: Dataset,
        output_root: Path,
        active_job_dataset_ids: set[str] | None = None,
    ) -> DatasetStatus:
        if dataset.status is DatasetStatus.archived:
            return DatasetStatus.archived

        if active_job_dataset_ids and str(dataset.id) in active_job_dataset_ids:
            return DatasetStatus.generating

        files = GenerationOrchestrator.list_generated_files(
            dataset_id=dataset.id,
            output_root=output_root,
        )
        return DatasetStatus.active if files else DatasetStatus.draft
