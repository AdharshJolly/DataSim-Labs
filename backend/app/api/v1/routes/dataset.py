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
    AttributeConfig,
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
    GenerationPreflightRequest,
    GenerationPreflightResponse,
    RetryGenerationJobResponse,
    ExplainRequest,
    ExplainResponse,
    SuggestionRequest,
    SuggestionResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services.dataset_repository import DatasetRepository
from app.services.generation_orchestrator import GenerationOrchestrator
from app.services.job_manager import JobManager
from app.services.suggestion_engine import SuggestionEngine
from app.services.template_service import TemplateService

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/templates", response_model=dict)
def get_templates() -> dict:
    """Get all available dataset templates."""
    try:
        templates = TemplateService.get_all_templates()
        return {"success": True, "templates": templates}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch templates: {str(exc)}"
        ) from exc


@router.post("/preflight", response_model=GenerationPreflightResponse)
def generation_preflight(
    payload: GenerationPreflightRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationPreflightResponse:
    try:
        preflight = GenerationOrchestrator.preflight_generation(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
            dataset_version_id=payload.dataset_version_id,
            row_count=payload.row_count,
            formats=payload.formats,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return GenerationPreflightResponse.model_validate(preflight)


@router.post("/create")
def create_dataset(
    payload: DatasetCreateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetCreateResponse:
    dataset = DatasetRepository.create_dataset(
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
        version = GenerationOrchestrator.create_dataset_version(
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
        preview_data = GenerationOrchestrator.generate_preview(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
            seed=payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "dataset_version_id": payload.dataset_version_id,
        "rows": len(preview_data.get("data", [])),
        "data": preview_data.get("data", []),
        "comparison": preview_data.get("comparison"),
    }


@router.post("/explain", response_model=ExplainResponse)
def explain_dataset_row(
    payload: ExplainRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExplainResponse:
    try:
        explanation = GenerationOrchestrator.explain_dataset_row(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
            row_index=payload.row_index,
            seed=payload.seed,
            column=payload.column,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ExplainResponse.model_validate(explanation)


@router.post("/suggestions", response_model=SuggestionResponse)
def suggest_dataset_settings(
    payload: SuggestionRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuggestionResponse:
    if payload.attributes:
        suggestion = SuggestionEngine.suggest(payload.attributes)
        return SuggestionResponse(
            dataset_version_id=payload.dataset_version_id,
            attribute_suggestions=suggestion.get("attribute_suggestions", []),
            relationship_suggestions=suggestion.get("relationship_suggestions", []),
            metadata=suggestion.get("metadata", {}),
        )

    if payload.dataset_version_id is None:
        raise HTTPException(
            status_code=400,
            detail="dataset_version_id is required when attributes are not provided",
        )

    try:
        DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    attrs = DatasetRepository.load_version_attributes(
        db=db,
        dataset_version_id=payload.dataset_version_id,
    )

    attributes = [
        {
            "name": item.name,
            "type": item.data_type,
            "description": item.description or "",
            "constraints": item.constraints_json or {},
            "distribution": item.distribution,
            "null_percentage": item.null_percentage,
        }
        for item in attrs
    ]

    validated_attributes = [
        AttributeConfig.model_validate(attribute) for attribute in attributes
    ]

    suggestion = SuggestionEngine.suggest(validated_attributes)
    return SuggestionResponse(
        dataset_version_id=payload.dataset_version_id,
        attribute_suggestions=suggestion.get("attribute_suggestions", []),
        relationship_suggestions=suggestion.get("relationship_suggestions", []),
        metadata=suggestion.get("metadata", {}),
    )


@router.post("/generate")
def generate_dataset(
    payload: GenerateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResponse:
    output_root = Path(settings.artifacts_dir)
    try:
        generation_result = GenerationOrchestrator.generate_dataset_files(
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "dataset_id": payload.dataset_id,
        "status": "completed",
        "row_count": payload.row_count,
        "files": generation_result.get("files", []),
        "quality_report": generation_result.get("quality_report"),
        "quality_dashboard": generation_result.get("quality_dashboard"),
        "validation_summary": generation_result.get("validation_summary"),
        "quality_guardrails": generation_result.get("quality_guardrails"),
        "generation_signature": generation_result.get("generation_signature"),
        "generation_run_id": generation_result.get("generation_run_id"),
        "comparison": generation_result.get("comparison"),
        "semantic_rule_metrics": generation_result.get("semantic_rule_metrics"),
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
        dataset = DatasetRepository.get_dataset(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
        )
        target_version_id = payload.dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        if not DatasetRepository.load_version_attributes(db, target_version_id):
            raise ValueError("Dataset version has no attributes")

        job = JobManager.create_generation_job(
            db=db,
            user_id=current_user.id,
            dataset_id=dataset.id,
            dataset_version_id=target_version_id,
            row_count=payload.row_count,
            formats=payload.formats,
            seed=payload.seed,
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


@router.get("/download/{dataset_id}", response_model=DownloadListResponse)
def download_dataset(
    dataset_id: uuid.UUID,
    format: str | None = Query(default=None),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    output_root = Path(settings.artifacts_dir)
    try:
        DatasetRepository.get_dataset(
            db=db, user_id=current_user.id, dataset_id=dataset_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if format:
        file_path = GenerationOrchestrator.resolve_generated_file(
            dataset_id=dataset_id,
            output_root=output_root,
            export_format=format,
        )
        if file_path is None:
            raise HTTPException(status_code=404, detail="Generated file not found")

        dataset_dir = (output_root / str(dataset_id)).resolve()
        resolved_file = file_path.resolve()
        if resolved_file.parent != dataset_dir:
            raise HTTPException(status_code=400, detail="Unsafe file path")

        safe_name = GenerationOrchestrator.sanitize_download_filename(file_path.name)
        return FileResponse(path=resolved_file, filename=safe_name)

    files = GenerationOrchestrator.list_generated_files(
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
    datasets = DatasetRepository.list_datasets(db=db, user_id=current_user.id)
    output_root = Path(settings.artifacts_dir)
    active_job_dataset_ids = JobManager.list_active_generation_job_dataset_ids(
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
                status=GenerationOrchestrator.resolve_effective_dataset_status(
                    dataset_id=dataset.id,
                    current_status=dataset.status,
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
        dataset = DatasetRepository.get_dataset(
            db=db,
            user_id=current_user.id,
            dataset_id=dataset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    output_root = Path(settings.artifacts_dir)
    active_job_dataset_ids = JobManager.list_active_generation_job_dataset_ids(
        db=db,
        user_id=current_user.id,
    )
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        latest_version_id=dataset.latest_version_id,
        status=GenerationOrchestrator.resolve_effective_dataset_status(
            dataset_id=dataset.id,
            current_status=dataset.status,
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
        versions = DatasetRepository.get_dataset_versions(
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
        DatasetRepository.delete_dataset(
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
        dataset = DatasetRepository.update_dataset_status(
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
