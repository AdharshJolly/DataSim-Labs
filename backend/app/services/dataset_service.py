"""
dataset_service.py

Public facade for dataset operations.
Delegates responsibilities to focused modules while preserving the existing API.
"""

import uuid
from pathlib import Path
from typing import Any

from pymongo.database import Database

from app.models.dataset import Dataset, DatasetStatus, DatasetVersion
from app.schemas.dataset import AttributeConfig
from app.services.dataset_repository import DatasetRepository
from app.services.generation_orchestrator import GenerationOrchestrator
from app.services.job_manager import JobManager


class DatasetService:
    """High-level API for dataset CRUD, generation, and job orchestration."""

    TERMINAL_JOB_STATUSES = JobManager.TERMINAL_JOB_STATUSES

    @staticmethod
    def create_dataset(
        db: Database,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Dataset:
        return DatasetRepository.create_dataset(
            db=db,
            user_id=user_id,
            name=name,
            description=description,
        )

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
    def delete_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        DatasetRepository.delete_dataset(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )

    @staticmethod
    def update_dataset_status(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        status: DatasetStatus,
    ) -> Dataset:
        return DatasetRepository.update_dataset_status(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            status=status,
        )

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
    def generate_preview(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.generate_preview(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
            seed=seed,
        )

    @staticmethod
    def preflight_generation(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        dataset_version_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.preflight_generation(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            row_count=row_count,
            formats=formats,
            dataset_version_id=dataset_version_id,
        )

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
        enforce_sync_limits: bool = True,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.generate_dataset_files(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            row_count=row_count,
            formats=formats,
            output_root=output_root,
            chunk_size=chunk_size,
            seed=seed,
            dataset_version_id=dataset_version_id,
            retention_hours=retention_hours,
            enforce_sync_limits=enforce_sync_limits,
        )

    @staticmethod
    def create_generation_job(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        seed: int | None = None,
        dataset_version_id: uuid.UUID | None = None,
        source_job_id: str | None = None,
    ) -> dict[str, Any]:
        dataset = DatasetRepository.get_dataset(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )
        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        if not DatasetRepository.load_version_attributes(db, target_version_id):
            raise ValueError("Dataset version has no attributes")

        return JobManager.create_generation_job(
            db=db,
            user_id=user_id,
            dataset_id=dataset.id,
            dataset_version_id=target_version_id,
            row_count=row_count,
            formats=formats,
            seed=seed,
            source_job_id=source_job_id,
        )

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
    def retry_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        return JobManager.retry_generation_job(db=db, user_id=user_id, job_id=job_id)

    @staticmethod
    def list_active_generation_job_dataset_ids(
        db: Database,
        user_id: uuid.UUID,
    ) -> set[str]:
        return JobManager.list_active_generation_job_dataset_ids(db=db, user_id=user_id)

    @staticmethod
    def cancel_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        return JobManager.cancel_generation_job(db=db, user_id=user_id, job_id=job_id)

    @staticmethod
    def mark_job_running(db: Database, job_id: str) -> dict[str, Any] | None:
        return JobManager.mark_job_running(db=db, job_id=job_id)

    @staticmethod
    def mark_job_cancelled(db: Database, job_id: str, stage: str = "cancelled") -> None:
        JobManager.mark_job_cancelled(db=db, job_id=job_id, stage=stage)

    @staticmethod
    def mark_job_completed(
        db: Database,
        job_id: str,
        result_payload: dict[str, Any],
    ) -> None:
        JobManager.mark_job_completed(
            db=db, job_id=job_id, result_payload=result_payload
        )

    @staticmethod
    def mark_job_failed(db: Database, job_id: str, message: str) -> None:
        JobManager.mark_job_failed(db=db, job_id=job_id, message=message)

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
    def sanitize_download_filename(file_name: str) -> str:
        return GenerationOrchestrator.sanitize_download_filename(file_name)

    @staticmethod
    def cleanup_old_artifacts(
        output_root: Path,
        max_age_hours: int,
        db: Database | None = None,
    ) -> None:
        GenerationOrchestrator.cleanup_old_artifacts(
            output_root=output_root,
            max_age_hours=max_age_hours,
            db=db,
        )

    @staticmethod
    def record_generation_artifacts(
        db: Database,
        dataset_id: uuid.UUID,
        generation_run_id: str,
        files: list[dict[str, Any]],
        retention_hours: int,
    ) -> None:
        GenerationOrchestrator.record_generation_artifacts(
            db=db,
            dataset_id=dataset_id,
            generation_run_id=generation_run_id,
            files=files,
            retention_hours=retention_hours,
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

    @staticmethod
    def evaluate_quality_guardrails(quality_report: dict[str, Any]) -> dict[str, Any]:
        return GenerationOrchestrator.evaluate_quality_guardrails(quality_report)

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
