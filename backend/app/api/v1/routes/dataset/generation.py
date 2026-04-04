from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pymongo.database import Database

from app.api.v1.dependencies import get_current_user, get_db
from app.auth.models import User
from app.core.config import settings
from app.engine.dataset_generator import DatasetGenerator
from app.schemas.dataset import (
    GenerateAsyncResponse,
    GenerateRequest,
    GenerateResponse,
    GenerationPreflightRequest,
    GenerationPreflightResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services.dataset_repository import DatasetRepository
from app.services.orchestration.generation_orchestrator import GenerationOrchestrator
from app.services.job_manager import JobManager
from app.services.orchestration.generation_orchestrator import (
    GenerationWorkflowOrchestrator,
)
from app.services.orchestration.preflight_orchestrator import PreflightOrchestrator
from app.services.orchestration.preview_orchestrator import PreviewOrchestrator
from app.services.orchestration.version_config import resolve_version_generation_config
from app.utils.attribute_utils import model_attributes_to_specs
from app.utils.response_builder import build_generation_response, build_preview_response

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.post("/preview")
def preview_dataset(
    payload: PreviewRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreviewResponse:
    try:
        preview_data = PreviewOrchestrator.run(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
            seed=payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        **build_preview_response(
            dataset_version_id=payload.dataset_version_id,
            data=preview_data.get("data", []),
            comparison=preview_data.get("comparison"),
        )
    }


@router.post("/preflight", response_model=GenerationPreflightResponse)
def generation_preflight(
    payload: GenerationPreflightRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationPreflightResponse:
    try:
        preflight = PreflightOrchestrator.run(
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


@router.post("/generate")
def generate_dataset(
    payload: GenerateRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResponse:
    output_root = Path(settings.artifacts_dir)
    try:
        generation_result = GenerationWorkflowOrchestrator.run(
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
        **build_generation_response(
            dataset_id=payload.dataset_id,
            row_count=payload.row_count,
            generation_result=generation_result,
        )
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

    from app.worker.tasks import generate_dataset_async_task

    generate_dataset_async_task.delay(str(job["_id"]))

    return {
        "job_id": str(job["_id"]),
        "status": "queued",
        "message": "Generation job queued",
    }


@router.get("/stream")
def stream_dataset_csv(
    dataset_version_id: uuid.UUID = Query(...),
    row_count: int = Query(..., ge=1, le=10000000),
    chunk_size: int = Query(default=50000, ge=1000, le=500000),
    seed: int | None = Query(default=None, ge=0),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    try:
        version = DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    attributes = DatasetRepository.load_version_attributes(
        db=db,
        dataset_version_id=dataset_version_id,
    )
    if not attributes:
        raise HTTPException(status_code=400, detail="Dataset version has no attributes")

    attribute_specs = model_attributes_to_specs(attributes)
    version_config = resolve_version_generation_config(
        config_json=version.config_json,
        available_columns=[attribute.name for attribute in attribute_specs],
    )

    generator_seed = seed if seed is not None else version.seed
    streaming_generator = DatasetGenerator(seed=generator_seed)

    def iter_csv() -> Any:
        remaining = row_count
        first_chunk = True
        while remaining > 0:
            current_chunk = min(chunk_size, remaining)
            frame = streaming_generator.generate_dataframe(
                attributes=attribute_specs,
                row_count=current_chunk,
                realism_rules=version_config.realism_rules,
                semantic_rules=version_config.semantic_rules,
            )
            csv_chunk = frame.to_csv(index=False, header=first_chunk)
            yield csv_chunk.encode("utf-8")
            first_chunk = False
            remaining -= current_chunk

    safe_file_name = f"dataset_{dataset_version_id}_stream.csv"
    response = StreamingResponse(iter_csv(), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_file_name}"'
    return response
