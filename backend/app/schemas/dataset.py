from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DataType(str, Enum):
    integer = "integer"
    float = "float"
    categorical = "categorical"
    boolean = "boolean"
    date = "date"
    text = "text"
    email = "email"
    name = "name"
    address = "address"


class DistributionType(str, Enum):
    uniform = "uniform"
    normal = "normal"
    skewed = "skewed"
    weighted_categorical = "weighted_categorical"


class AttributeConfig(BaseModel):
    name: str = Field(..., min_length=1)
    type: DataType
    description: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    distribution: DistributionType = DistributionType.uniform
    null_percentage: float = Field(default=0.0, ge=0.0, le=100.0)


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None


class DatasetAttributesRequest(BaseModel):
    dataset_id: UUID
    attributes: list[AttributeConfig]


class PreviewRequest(BaseModel):
    dataset_version_id: UUID


class PreviewResponse(BaseModel):
    dataset_version_id: UUID
    rows: int
    data: list[dict[str, Any]]


class GenerateRequest(BaseModel):
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    row_count: int = Field(..., ge=1, le=10000000)
    formats: list[str] = Field(default_factory=lambda: ["csv"])
    async_mode: bool = False


class GeneratedFileInfo(BaseModel):
    format: str
    file_name: str
    file_path: str
    size_bytes: int


class GenerateResponse(BaseModel):
    dataset_id: UUID
    status: str
    row_count: int
    job_id: str | None = None
    message: str | None = None
    files: list[GeneratedFileInfo]


class GenerationStatusResponse(BaseModel):
    dataset_id: UUID
    status: str
    row_count: int | None = None
    files: list[GeneratedFileInfo] = Field(default_factory=list)
    message: str | None = None


class DownloadListResponse(BaseModel):
    dataset_id: UUID
    files: list[GeneratedFileInfo]


class DatasetCreateResponse(BaseModel):
    message: str
    dataset_id: UUID
    name: str


class DatasetAttributesResponse(BaseModel):
    message: str
    dataset_id: UUID
    version_id: UUID
    version_number: int
    attribute_count: int


class DatasetSummaryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    latest_version_id: UUID | None
    created_at: str


class DatasetVersionSummaryResponse(BaseModel):
    id: UUID
    version_number: int
    config_json: dict[str, Any]
    created_at: str


class DatasetDetailResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    latest_version_id: UUID | None
    created_at: str
    updated_at: str


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummaryResponse]


class DatasetVersionsResponse(BaseModel):
    dataset_id: UUID
    versions: list[DatasetVersionSummaryResponse]
