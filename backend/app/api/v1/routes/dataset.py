from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dataset import (
    DatasetAttributesRequest,
    DatasetAttributesResponse,
    DatasetCreateRequest,
    DatasetCreateResponse,
    GenerateRequest,
    PreviewRequest,
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
def preview_dataset(payload: PreviewRequest) -> dict[str, str | int]:
    return {
        "message": "Preview generated (scaffold)",
        "rows": 10,
        "columns": len(payload.attributes),
    }


@router.post("/generate")
def generate_dataset(payload: GenerateRequest) -> dict[str, str | int]:
    return {
        "message": "Generation queued (scaffold)",
        "dataset_id": payload.dataset_id,
        "row_count": payload.row_count,
    }


@router.get("/download/{dataset_id}")
def download_dataset(dataset_id: str) -> dict[str, str]:
    return {
        "message": "Download endpoint scaffold",
        "dataset_id": dataset_id,
    }
