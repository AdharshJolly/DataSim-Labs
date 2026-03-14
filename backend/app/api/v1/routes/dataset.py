import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi import Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.dataset import (
    DatasetAttributesRequest,
    DatasetAttributesResponse,
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
) -> DatasetCreateResponse:
    dataset = DatasetService.create_dataset(
        db=db, name=payload.name, description=payload.description
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
) -> DatasetAttributesResponse:
    try:
        version = DatasetService.create_dataset_version(
            db=db,
            dataset_id=payload.dataset_id,
            attributes=payload.attributes,
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
) -> PreviewResponse:
    try:
        preview_data = DatasetService.generate_preview(
            db=db,
            dataset_version_id=payload.dataset_version_id,
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
) -> GenerateResponse:
    output_root = Path(settings.artifacts_dir)
    try:
        files = DatasetService.generate_dataset_files(
            db=db,
            dataset_id=payload.dataset_id,
            row_count=payload.row_count,
            formats=payload.formats,
            output_root=output_root,
            chunk_size=settings.generation_chunk_size,
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
) -> Any:
    output_root = Path(settings.artifacts_dir)
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
