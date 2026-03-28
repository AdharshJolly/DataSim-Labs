import uuid
from pathlib import Path

from app.core.config import settings
from app.db.session import database
from app.services.dataset_service import DatasetService
from app.worker.celery_app import celery_app


@celery_app.task(name="dataset.generate_async")
def generate_dataset_async_task(job_id: str) -> None:
    job = database["dataset_generation_jobs"].find_one({"_id": job_id})
    if job is None:
        return

    if bool(job.get("cancel_requested")) or str(job.get("status")) == "cancelled":
        DatasetService.mark_job_cancelled(db=database, job_id=job_id)
        return

    running_job = DatasetService.mark_job_running(db=database, job_id=job_id)
    if running_job is None:
        return

    if bool(running_job.get("cancel_requested")):
        DatasetService.mark_job_cancelled(db=database, job_id=job_id)
        return

    try:
        result = DatasetService.generate_dataset_files(
            db=database,
            user_id=uuid.UUID(str(running_job["user_id"])),
            dataset_id=uuid.UUID(str(running_job["dataset_id"])),
            dataset_version_id=(
                uuid.UUID(str(running_job["dataset_version_id"]))
                if running_job.get("dataset_version_id")
                else None
            ),
            row_count=int(running_job["row_count"]),
            formats=[str(item) for item in running_job.get("formats", ["csv"])],
            output_root=Path(settings.artifacts_dir),
            chunk_size=settings.generation_chunk_size,
            seed=(
                int(running_job["seed"])
                if running_job.get("seed") is not None
                else None
            ),
            retention_hours=settings.artifact_retention_hours,
            drift_profile=(
                dict(running_job.get("drift_profile", {}))
                if isinstance(running_job.get("drift_profile"), dict)
                else None
            ),
            enforce_sync_limits=False,
        )
        DatasetService.mark_job_completed(
            db=database,
            job_id=job_id,
            result_payload={
                "dataset_id": str(running_job["dataset_id"]),
                "status": "completed",
                "row_count": int(running_job["row_count"]),
                "files": result.get("files", []),
                "quality_report": result.get("quality_report"),
                "quality_dashboard": result.get("quality_dashboard"),
                "validation_summary": result.get("validation_summary"),
                "quality_guardrails": result.get("quality_guardrails"),
                "drift_simulation": result.get("drift_simulation"),
                "generation_signature": result.get("generation_signature"),
                "generation_run_id": result.get("generation_run_id"),
                "comparison": result.get("comparison"),
            },
        )
    except ValueError as exc:
        DatasetService.mark_job_failed(db=database, job_id=job_id, message=str(exc))
    except Exception:
        DatasetService.mark_job_failed(
            db=database,
            job_id=job_id,
            message="Generation worker encountered an unexpected error.",
        )
