from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.api.v1.dependencies import get_current_user, get_db
from app.auth.models import User
from app.schemas.dataset import (
    CancelGenerationJobResponse,
    GenerationJobListResponse,
    GenerationJobResponse,
    RetryGenerationJobResponse,
)
from app.services.job_manager import JobManager

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/jobs", response_model=GenerationJobListResponse)
def list_generation_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJobListResponse:
    jobs = JobManager.list_generation_jobs(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )
    return {
        "jobs": [JobManager.serialize_generation_job(job) for job in jobs],
    }


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
def get_generation_job(
    job_id: str,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJobResponse:
    try:
        job = JobManager.get_generation_job(
            db=db,
            user_id=current_user.id,
            job_id=job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JobManager.serialize_generation_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=CancelGenerationJobResponse)
def cancel_generation_job(
    job_id: str,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CancelGenerationJobResponse:
    try:
        job = JobManager.cancel_generation_job(
            db=db,
            user_id=current_user.id,
            job_id=job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    status = str(job.get("status", "queued"))
    return {
        "job_id": job_id,
        "status": status,
        "cancel_requested": bool(job.get("cancel_requested", False)),
        "message": (
            "Job already finished"
            if status in JobManager.TERMINAL_JOB_STATUSES
            else "Cancellation requested"
        ),
    }


@router.post("/jobs/{job_id}/retry", response_model=RetryGenerationJobResponse)
def retry_generation_job(
    job_id: str,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetryGenerationJobResponse:
    try:
        new_job = JobManager.retry_generation_job(
            db=db,
            user_id=current_user.id,
            job_id=job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from app.worker.tasks import generate_dataset_async_task

    generate_dataset_async_task.delay(str(new_job["_id"]))

    return {
        "original_job_id": job_id,
        "new_job_id": str(new_job["_id"]),
        "status": "queued",
        "message": "Retry job queued",
    }
