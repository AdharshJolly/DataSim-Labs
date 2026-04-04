from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.api.v1.dependencies import get_current_user, get_db
from app.auth.models import User
from app.core.config import settings
from app.schemas.dataset import (
    DatasetAttributesRequest,
    DatasetAttributesResponse,
    DatasetCreateRequest,
    DatasetCreateResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetStatusUpdateRequest,
    DatasetSummaryResponse,
    DatasetVersionSummaryResponse,
    DatasetVersionsResponse,
)
from app.services.dataset_repository import DatasetRepository
from app.services.orchestration.generation_orchestrator import GenerationOrchestrator
from app.services.job_manager import JobManager

router = APIRouter(prefix="/dataset", tags=["dataset"])


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
