from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import DatasetStatus
from app.schemas.generation import DownloadListResponse


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None


class DatasetCreateResponse(BaseModel):
    message: str
    dataset_id: UUID
    name: str


class DatasetSummaryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    latest_version_id: UUID | None
    status: DatasetStatus
    created_at: str


class DatasetVersionSummaryResponse(BaseModel):
    id: UUID
    version_number: int
    seed: int | None
    config_json: dict[str, Any]
    created_at: str


class DatasetDetailResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    latest_version_id: UUID | None
    status: DatasetStatus
    created_at: str
    updated_at: str


class DatasetStatusUpdateRequest(BaseModel):
    status: DatasetStatus


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummaryResponse]


class DatasetVersionsResponse(BaseModel):
    dataset_id: UUID
    versions: list[DatasetVersionSummaryResponse]


__all__ = [
    "DatasetCreateRequest",
    "DatasetCreateResponse",
    "DatasetSummaryResponse",
    "DatasetDetailResponse",
    "DatasetVersionSummaryResponse",
    "DatasetListResponse",
    "DatasetVersionsResponse",
    "DatasetStatusUpdateRequest",
    "DownloadListResponse",
]
