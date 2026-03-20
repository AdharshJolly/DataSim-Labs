import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi import Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pymongo.database import Database

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import settings
from app.db.session import get_db
from app.schemas.dataset import (
    CancelGenerationJobResponse,
    DatasetAttributesRequest,
    DatasetAttributesResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetStatusUpdateRequest,
    DatasetSummaryResponse,
    DatasetVersionSummaryResponse,
    DatasetVersionsResponse,
    DownloadListResponse,
    GenerateAsyncResponse,
    GenerationJobListResponse,
    DatasetCreateRequest,
    DatasetCreateResponse,
    GenerationJobResponse,
    GenerateRequest,
    GenerateResponse,
    RetryGenerationJobResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.post("/create")
def create_dataset(
    payload: DatasetCreateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetCreateResponse:
    dataset = DatasetService.create_dataset(
        db=db,
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    return {
        "message": "Dataset created",
        "dataset_id": dataset.id,
        "name": dataset.name,
    }


@router.post("/attributes")
def save_attributes(
    payload: DatasetAttributesRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetAttributesResponse:
    try:
        version = DatasetService.create_dataset_version(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
            attributes=payload.attributes,
            seed=payload.seed,
            correlations=[
                rule.model_dump(mode="json") for rule in payload.correlations
            ],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "message": "Attributes saved",
        "dataset_id": payload.dataset_id,
        "version_id": version.id,
        "version_number": version.version_number,
        "attribute_count": len(payload.attributes),
    }


@router.post("/preview")
def preview_dataset(
    payload: PreviewRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreviewResponse:
    try:
        preview_data = DatasetService.generate_preview(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
            seed=payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "dataset_version_id": payload.dataset_version_id,
        "rows": 10,
        "data": preview_data,
    }


@router.post("/generate")
def generate_dataset(
    payload: GenerateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResponse:
    output_root = Path(settings.artifacts_dir)
    try:
        generation_result = DatasetService.generate_dataset_files(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
            dataset_version_id=payload.dataset_version_id,
            row_count=payload.row_count,
            formats=payload.formats,
            output_root=output_root,
            chunk_size=settings.generation_chunk_size,
            seed=payload.seed,
            retention_hours=settings.artifact_retention_hours,
            drift_profile=(
                payload.drift_profile.model_dump(mode="json")
                if payload.drift_profile
                else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "dataset_id": payload.dataset_id,
        "status": "completed",
        "row_count": payload.row_count,
        "files": generation_result.get("files", []),
        "quality_report": generation_result.get("quality_report"),
        "quality_guardrails": generation_result.get("quality_guardrails"),
        "drift_simulation": generation_result.get("drift_simulation"),
        "generation_signature": generation_result.get("generation_signature"),
        "generation_run_id": generation_result.get("generation_run_id"),
        "comparison": generation_result.get("comparison"),
    }


@router.post("/generate-async", response_model=GenerateAsyncResponse)
def generate_dataset_async(
    payload: GenerateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateAsyncResponse:
    if not settings.async_generation_enabled:
        raise HTTPException(
            status_code=503,
            detail="Async generation is disabled. Set ASYNC_GENERATION_ENABLED=true.",
        )

    try:
        job = DatasetService.create_generation_job(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
            dataset_version_id=payload.dataset_version_id,
            row_count=payload.row_count,
            formats=payload.formats,
            seed=payload.seed,
            drift_profile=(
                payload.drift_profile.model_dump(mode="json")
                if payload.drift_profile
                else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Deferred import keeps the API bootable even when worker dependencies are absent.
    from app.worker.tasks import generate_dataset_async_task

    generate_dataset_async_task.delay(str(job["_id"]))

    return {
        "job_id": str(job["_id"]),
        "status": "queued",
        "message": "Generation job queued",
    }


@router.get("/jobs", response_model=GenerationJobListResponse)
def list_generation_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJobListResponse:
    jobs = DatasetService.list_generation_jobs(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )
    return {
        "jobs": [DatasetService.serialize_generation_job(job) for job in jobs],
    }


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
def get_generation_job(
    job_id: str,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJobResponse:
    try:
        job = DatasetService.get_generation_job(
            db=db,
            user_id=current_user.id,
            job_id=job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DatasetService.serialize_generation_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=CancelGenerationJobResponse)
def cancel_generation_job(
    job_id: str,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CancelGenerationJobResponse:
    try:
        job = DatasetService.cancel_generation_job(
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
            if status in DatasetService.TERMINAL_JOB_STATUSES
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
        new_job = DatasetService.retry_generation_job(
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


@router.get("/download/{dataset_id}", response_model=DownloadListResponse)
def download_dataset(
    dataset_id: uuid.UUID,
    format: str | None = Query(default=None),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    output_root = Path(settings.artifacts_dir)
    try:
        DatasetService.get_dataset(
            db=db, user_id=current_user.id, dataset_id=dataset_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if format:
        file_path = DatasetService.resolve_generated_file(
            dataset_id=dataset_id,
            output_root=output_root,
            export_format=format,
        )
        if file_path is None:
            raise HTTPException(status_code=404, detail="Generated file not found")
        return FileResponse(path=file_path, filename=file_path.name)

    files = DatasetService.list_generated_files(
        dataset_id=dataset_id, output_root=output_root
    )
    return {
        "dataset_id": dataset_id,
        "files": files,
    }


@router.get("/list", response_model=DatasetListResponse)
def list_datasets(
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetListResponse:
    datasets = DatasetService.list_datasets(db=db, user_id=current_user.id)
    output_root = Path(settings.artifacts_dir)
    active_job_dataset_ids = DatasetService.list_active_generation_job_dataset_ids(
        db=db,
        user_id=current_user.id,
    )
    return {
        "datasets": [
            DatasetSummaryResponse(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                latest_version_id=dataset.latest_version_id,
                status=DatasetService.resolve_effective_dataset_status(
                    dataset=dataset,
                    output_root=output_root,
                    active_job_dataset_ids=active_job_dataset_ids,
                ),
                created_at=dataset.created_at.isoformat(),
            )
            for dataset in datasets
        ]
    }


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetDetailResponse:
    try:
        dataset = DatasetService.get_dataset(
            db=db,
            user_id=current_user.id,
            dataset_id=dataset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    output_root = Path(settings.artifacts_dir)
    active_job_dataset_ids = DatasetService.list_active_generation_job_dataset_ids(
        db=db,
        user_id=current_user.id,
    )
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        latest_version_id=dataset.latest_version_id,
        status=DatasetService.resolve_effective_dataset_status(
            dataset=dataset,
            output_root=output_root,
            active_job_dataset_ids=active_job_dataset_ids,
        ),
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
    )


@router.get("/{dataset_id}/versions", response_model=DatasetVersionsResponse)
def get_dataset_versions(
    dataset_id: uuid.UUID,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetVersionsResponse:
    try:
        versions = DatasetService.get_dataset_versions(
            db=db,
            user_id=current_user.id,
            dataset_id=dataset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "dataset_id": dataset_id,
        "versions": [
            DatasetVersionSummaryResponse(
                id=version.id,
                version_number=version.version_number,
                seed=version.seed,
                config_json=version.config_json,
                created_at=version.created_at.isoformat(),
            )
            for version in versions
        ],
    }


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        DatasetService.delete_dataset(
            db=db, user_id=current_user.id, dataset_id=dataset_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": "Dataset deleted"}


@router.patch("/{dataset_id}/status", response_model=DatasetDetailResponse)
def update_dataset_status(
    dataset_id: uuid.UUID,
    payload: DatasetStatusUpdateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetDetailResponse:
    try:
        dataset = DatasetService.update_dataset_status(
            db=db,
            user_id=current_user.id,
            dataset_id=dataset_id,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        latest_version_id=dataset.latest_version_id,
        status=dataset.status,
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
    )

from fastapi import File, UploadFile
from app.services.profile_service import ProfileService

@router.post("/{dataset_version_id}/profile/upload")
def upload_dataset_profile(
    dataset_version_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        profile = ProfileService.process_and_save_profile(
            db=db,
            dataset_version_id=dataset_version_id,
            file=file
        )
        return {"message": "Profile learned successfully", "profile": profile}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/{dataset_version_id}/profile")
def get_dataset_profile(
    dataset_version_id: uuid.UUID,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        profile = ProfileService.get_profile(
            db=db,
            dataset_version_id=dataset_version_id
        )
        return profile
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/{dataset_version_id}/profile/generate")
def generate_from_profile(
    dataset_version_id: uuid.UUID,
    row_count: int = Query(default=10, ge=1, le=1000),
    seed: int | None = Query(default=None),
    enable_feedback_loop: bool = Query(default=True),
    max_iterations: int = Query(default=3, ge=1, le=10),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        response_data = ProfileService.generate_from_profile(
            db=db,
            dataset_version_id=dataset_version_id,
            row_count=row_count,
            seed=seed,
            enable_feedback_loop=enable_feedback_loop,
            max_iterations=max_iterations
        )
        return response_data
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

from pydantic import BaseModel
from app.services.template_service import TemplateService
from app.services.copilot_service import CoPilotService

class CopilotRequest(BaseModel):
    prompt: str

@router.get("/templates")
def get_templates(
    current_user: User = Depends(get_current_user),
):
    return {
        "templates": TemplateService.get_all_templates(),
        "personas": TemplateService.get_all_personas()
    }

@router.post("/copilot/generate-profile")
def copilot_generate_profile(
    payload: CopilotRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        profile = CoPilotService.generate_profile_from_prompt(payload.prompt)
        return {"message": "AI generation successful", "profile": profile}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
