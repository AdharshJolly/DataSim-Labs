from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pymongo.database import Database

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.schemas.dataset import (
    CompareRequest,
    CompareResponse,
    DownloadListResponse,
    ExplainRequest,
    ExplainResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackSummaryResponse,
    SuggestionRequest,
    SuggestionResponse,
)
from app.services.dataset_repository import DatasetRepository
from app.services.dataset_service import DatasetService
from app.services.feedback_service import FeedbackService
from app.services.orchestration.generation_orchestrator import GenerationOrchestrator
from app.services.orchestration.explain_orchestrator import ExplainOrchestrator
from app.services.template_service import TemplateService
from app.utils.response_builder import build_preview_response
from app.core.config import settings

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/templates", response_model=dict)
def get_templates() -> dict:
    try:
        templates = TemplateService.get_all_templates()
        return {"success": True, "templates": templates}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch templates: {str(exc)}"
        ) from exc


@router.post("/explain", response_model=ExplainResponse)
def explain_dataset_row(
    payload: ExplainRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExplainResponse:
    try:
        explanation = ExplainOrchestrator.run(
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
    try:
        suggestion = DatasetService.suggest_dataset_settings(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
            attributes=payload.attributes,
        )
    except ValueError as exc:
        status_code = 400 if "required" in str(exc).lower() else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return SuggestionResponse(
        dataset_version_id=payload.dataset_version_id,
        attribute_suggestions=suggestion.get("attribute_suggestions", []),
        relationship_suggestions=suggestion.get("relationship_suggestions", []),
        metadata=suggestion.get("metadata", {}),
    )


@router.post("/compare", response_model=CompareResponse)
def compare_dataset_output(
    payload: CompareRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompareResponse:
    try:
        comparison = DatasetService.compare_dataset_output(
            db=db,
            user_id=current_user.id,
            dataset_version_id=payload.dataset_version_id,
            sample_rows=payload.sample_rows,
            seed=payload.seed,
            generated_data=payload.generated_data,
        )
    except ValueError as exc:
        status_code = 400 if "no attributes" in str(exc).lower() else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return CompareResponse(
        dataset_version_id=payload.dataset_version_id,
        overall_drift_score=float(comparison.get("overall_drift_score", 0.0)),
        metrics=comparison.get("metrics", []),
        recommendations=comparison.get("recommendations", []),
    )


@router.post("/feedback", response_model=FeedbackResponse)
def submit_dataset_feedback(
    payload: FeedbackRequest,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    try:
        DatasetRepository.get_dataset(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    created = FeedbackService.submit_feedback(
        db=db,
        user_id=current_user.id,
        dataset_id=payload.dataset_id,
        dataset_version_id=payload.dataset_version_id,
        rating=payload.rating,
        comment=payload.comment,
        generation_signature=payload.generation_signature,
        config_snapshot=payload.config_snapshot,
    )

    return FeedbackResponse(
        feedback_id=str(created.get("_id")),
        dataset_id=payload.dataset_id,
        dataset_version_id=payload.dataset_version_id,
        rating=payload.rating,
        comment=payload.comment,
        message="Feedback submitted",
    )


@router.get("/feedback-summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(
    dataset_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackSummaryResponse:
    if dataset_id is not None:
        try:
            DatasetRepository.get_dataset(
                db=db,
                user_id=current_user.id,
                dataset_id=dataset_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    summary = FeedbackService.summarize_feedback(
        db=db,
        user_id=current_user.id,
        dataset_id=dataset_id,
        limit=limit,
    )
    return FeedbackSummaryResponse(
        dataset_id=dataset_id,
        count=int(summary.get("count", 0)),
        average_rating=summary.get("average_rating"),
        ratings=summary.get("ratings", []),
        recent=summary.get("recent", []),
    )


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
