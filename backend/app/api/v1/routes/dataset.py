import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi import Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import settings
from app.db.session import get_db
from app.schemas.dataset import (
    DatasetAttributesRequest,
    DatasetAttributesResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetStatusUpdateRequest,
    DatasetSummaryResponse,
    DatasetVersionSummaryResponse,
    DatasetVersionsResponse,
    DownloadListResponse,
    DatasetCreateRequest,
    DatasetCreateResponse,
    GenerateRequest,
    GenerateResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.post("/create")
def create_dataset(
    payload: DatasetCreateRequest,
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetAttributesResponse:
    try:
        version = DatasetService.create_dataset_version(
            db=db,
            user_id=current_user.id,
            dataset_id=payload.dataset_id,
            attributes=payload.attributes,
            seed=payload.seed,
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResponse:
    output_root = Path(settings.artifacts_dir)
    try:
        files = DatasetService.generate_dataset_files(
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
        "files": files,
    }


@router.get("/download/{dataset_id}", response_model=DownloadListResponse)
def download_dataset(
    dataset_id: uuid.UUID,
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetListResponse:
    datasets = DatasetService.list_datasets(db=db, user_id=current_user.id)
    return {
        "datasets": [
            DatasetSummaryResponse(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                latest_version_id=dataset.latest_version_id,
                status=dataset.status,
                created_at=dataset.created_at.isoformat(),
            )
            for dataset in datasets
        ]
    }


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
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

    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        latest_version_id=dataset.latest_version_id,
        status=dataset.status,
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
    )


@router.get("/{dataset_id}/versions", response_model=DatasetVersionsResponse)
def get_dataset_versions(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
