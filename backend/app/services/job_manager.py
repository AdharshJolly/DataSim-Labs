"""
job_manager.py

Manages dataset generation job lifecycle and status tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import DESCENDING, ReturnDocument
from pymongo.database import Database


class JobManager:
    """Manages dataset generation job creation, tracking, and status updates."""

    TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled"}

    @staticmethod
    def create_generation_job(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        seed: int | None = None,
        source_job_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new generation job."""
        now = datetime.now(timezone.utc)
        job_id = str(uuid.uuid4())
        document: dict[str, Any] = {
            "_id": job_id,
            "user_id": str(user_id),
            "dataset_id": str(dataset_id),
            "dataset_version_id": str(dataset_version_id),
            "row_count": row_count,
            "formats": sorted([fmt.lower() for fmt in formats]),
            "seed": seed,
            "source_job_id": source_job_id,
            "status": "queued",
            "stage": "queued",
            "progress_percentage": 0,
            "cancel_requested": False,
            "error": None,
            "result": None,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
        }
        db["dataset_generation_jobs"].insert_one(document)
        return document

    @staticmethod
    def list_generation_jobs(
        db: Database,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List generation jobs for a user."""
        max_limit = max(1, min(limit, 100))
        cursor = (
            db["dataset_generation_jobs"]
            .find({"user_id": str(user_id)})
            .sort("created_at", DESCENDING)
            .limit(max_limit)
        )
        return list(cursor)

    @staticmethod
    def get_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        """Get a specific generation job."""
        document = db["dataset_generation_jobs"].find_one(
            {"_id": job_id, "user_id": str(user_id)}
        )
        if document is None:
            raise ValueError("Generation job not found")
        return document

    @staticmethod
    def retry_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        """Create a new job based on a previous job's configuration."""
        job = JobManager.get_generation_job(db=db, user_id=user_id, job_id=job_id)
        status = str(job.get("status", "queued"))
        if status not in {"failed", "cancelled", "completed"}:
            raise ValueError("Only failed, cancelled, or completed jobs can be retried")

        return JobManager.create_generation_job(
            db=db,
            user_id=user_id,
            dataset_id=uuid.UUID(str(job["dataset_id"])),
            dataset_version_id=(
                uuid.UUID(str(job["dataset_version_id"]))
                if job.get("dataset_version_id")
                else uuid.UUID(str(job["dataset_id"]))
            ),
            row_count=int(job["row_count"]),
            formats=[str(item) for item in job.get("formats", ["csv"])],
            seed=(int(job["seed"]) if job.get("seed") is not None else None),
            source_job_id=job_id,
        )

    @staticmethod
    def list_active_generation_job_dataset_ids(
        db: Database,
        user_id: uuid.UUID,
    ) -> set[str]:
        """Get dataset IDs with active generation jobs."""
        rows = db["dataset_generation_jobs"].find(
            {"user_id": str(user_id)},
            {"dataset_id": 1, "status": 1, "created_at": 1, "updated_at": 1},
        )

        latest_by_dataset: dict[str, dict[str, Any]] = {}
        for row in rows:
            dataset_id = str(row.get("dataset_id", ""))
            if not dataset_id:
                continue

            existing = latest_by_dataset.get(dataset_id)
            if existing is None:
                latest_by_dataset[dataset_id] = row
                continue

            current_created = row.get("created_at")
            existing_created = existing.get("created_at")
            current_updated = row.get("updated_at")
            existing_updated = existing.get("updated_at")

            if (
                isinstance(current_created, datetime)
                and isinstance(existing_created, datetime)
                and current_created > existing_created
            ):
                latest_by_dataset[dataset_id] = row
                continue

            if isinstance(current_created, datetime) and not isinstance(
                existing_created, datetime
            ):
                latest_by_dataset[dataset_id] = row
                continue

            if (
                isinstance(current_created, datetime)
                and isinstance(existing_created, datetime)
                and current_created == existing_created
                and isinstance(current_updated, datetime)
                and isinstance(existing_updated, datetime)
                and current_updated > existing_updated
            ):
                latest_by_dataset[dataset_id] = row

        active_statuses = {"queued", "running"}
        return {
            dataset_id
            for dataset_id, job in latest_by_dataset.items()
            if str(job.get("status", "")) in active_statuses
        }

    @staticmethod
    def cancel_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        """Request cancellation of a generation job."""
        job = JobManager.get_generation_job(db=db, user_id=user_id, job_id=job_id)
        now = datetime.now(timezone.utc)
        status = str(job.get("status", "queued"))

        if status in JobManager.TERMINAL_JOB_STATUSES:
            return job

        update: dict[str, Any] = {
            "cancel_requested": True,
            "updated_at": now,
            "stage": "cancel_requested",
        }

        if status == "queued":
            update["status"] = "cancelled"
            update["progress_percentage"] = 100
            update["finished_at"] = now
            update["stage"] = "cancelled"

        db["dataset_generation_jobs"].update_one(
            {"_id": job_id, "user_id": str(user_id)},
            {"$set": update},
        )
        return JobManager.get_generation_job(db=db, user_id=user_id, job_id=job_id)

    @staticmethod
    def mark_job_running(db: Database, job_id: str) -> dict[str, Any] | None:
        """Mark a job as running."""
        now = datetime.now(timezone.utc)
        result = db["dataset_generation_jobs"].find_one_and_update(
            {
                "_id": job_id,
                "status": {"$in": ["queued", "running"]},
            },
            {
                "$set": {
                    "status": "running",
                    "stage": "generating",
                    "progress_percentage": 10,
                    "updated_at": now,
                    "started_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return result

    @staticmethod
    def mark_job_cancelled(db: Database, job_id: str, stage: str = "cancelled") -> None:
        """Mark a job as cancelled."""
        now = datetime.now(timezone.utc)
        db["dataset_generation_jobs"].update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "cancelled",
                    "stage": stage,
                    "progress_percentage": 100,
                    "cancel_requested": True,
                    "updated_at": now,
                    "finished_at": now,
                }
            },
        )

    @staticmethod
    def mark_job_completed(
        db: Database,
        job_id: str,
        result_payload: dict[str, Any],
    ) -> None:
        """Mark a job as completed."""
        now = datetime.now(timezone.utc)
        db["dataset_generation_jobs"].update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "stage": "completed",
                    "progress_percentage": 100,
                    "updated_at": now,
                    "finished_at": now,
                    "result": result_payload,
                    "error": None,
                }
            },
        )

    @staticmethod
    def mark_job_failed(db: Database, job_id: str, message: str) -> None:
        """Mark a job as failed."""
        now = datetime.now(timezone.utc)
        db["dataset_generation_jobs"].update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "stage": "failed",
                    "progress_percentage": 100,
                    "updated_at": now,
                    "finished_at": now,
                    "error": message,
                }
            },
        )

    @staticmethod
    def serialize_generation_job(job: dict[str, Any]) -> dict[str, Any]:
        """Serialize a job document for API response."""
        result_payload = job.get("result")
        if not isinstance(result_payload, dict):
            result_payload = None

        def _iso(value: Any) -> str | None:
            if isinstance(value, datetime):
                return value.isoformat()
            return None

        return {
            "job_id": str(job.get("_id")),
            "dataset_id": uuid.UUID(str(job.get("dataset_id"))),
            "dataset_version_id": (
                uuid.UUID(str(job.get("dataset_version_id")))
                if job.get("dataset_version_id")
                else None
            ),
            "status": str(job.get("status", "queued")),
            "stage": str(job.get("stage", "queued")),
            "progress_percentage": int(job.get("progress_percentage", 0)),
            "row_count": int(job.get("row_count", 0)),
            "formats": [str(item) for item in job.get("formats", [])],
            "seed": job.get("seed"),
            "cancel_requested": bool(job.get("cancel_requested", False)),
            "created_at": _iso(job.get("created_at"))
            or datetime.now(timezone.utc).isoformat(),
            "started_at": _iso(job.get("started_at")),
            "finished_at": _iso(job.get("finished_at")),
            "error": str(job.get("error")) if job.get("error") else None,
            "result": result_payload,
        }
