from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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


class DatasetStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class AttributeConfig(BaseModel):
    name: str = Field(..., min_length=1)
    type: DataType
    description: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    distribution: DistributionType = DistributionType.uniform
    null_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_constraints(self) -> "AttributeConfig":
        allowed_keys: set[str] = set()
        if self.type in {DataType.integer, DataType.float}:
            allowed_keys = {"min", "max"}
            min_value = self.constraints.get("min")
            max_value = self.constraints.get("max")
            if min_value is not None and not isinstance(min_value, (int, float)):
                raise ValueError("Numeric attributes require numeric 'min'")
            if max_value is not None and not isinstance(max_value, (int, float)):
                raise ValueError("Numeric attributes require numeric 'max'")
            if (
                min_value is not None
                and max_value is not None
                and float(min_value) > float(max_value)
            ):
                raise ValueError("Numeric attribute 'min' cannot be greater than 'max'")
        elif self.type is DataType.categorical:
            allowed_keys = {"categories", "weights"}
            categories = self.constraints.get("categories")
            weights = self.constraints.get("weights")
            if categories is not None and (
                not isinstance(categories, list)
                or not all(
                    isinstance(item, str) and item.strip() for item in categories
                )
            ):
                raise ValueError(
                    "Categorical attributes require string array 'categories'"
                )
            if weights is not None and (
                not isinstance(weights, list)
                or not all(isinstance(item, (int, float)) for item in weights)
            ):
                raise ValueError(
                    "Categorical attributes require numeric array 'weights'"
                )
            if isinstance(categories, list) and isinstance(weights, list):
                if len(categories) != len(weights):
                    raise ValueError("'weights' length must match 'categories' length")
                if sum(float(weight) for weight in weights) <= 0:
                    raise ValueError(
                        "Categorical 'weights' must sum to a positive value"
                    )
        elif self.type is DataType.date:
            allowed_keys = {"start_date", "end_date"}
            start_date = self.constraints.get("start_date")
            end_date = self.constraints.get("end_date")
            if start_date is not None and not isinstance(start_date, str):
                raise ValueError("Date attributes require string 'start_date'")
            if end_date is not None and not isinstance(end_date, str):
                raise ValueError("Date attributes require string 'end_date'")
            if isinstance(start_date, str) and isinstance(end_date, str):
                if date.fromisoformat(start_date) > date.fromisoformat(end_date):
                    raise ValueError(
                        "Date attribute 'start_date' cannot be after 'end_date'"
                    )

        unknown_keys = set(self.constraints.keys()) - allowed_keys
        if unknown_keys:
            keys = ", ".join(sorted(unknown_keys))
            raise ValueError(
                f"Unsupported constraint keys for {self.type.value}: {keys}"
            )

        if (
            self.distribution is DistributionType.weighted_categorical
            and self.type is not DataType.categorical
        ):
            raise ValueError(
                "'weighted_categorical' distribution is only valid for categorical type"
            )

        if (
            self.type
            in {
                DataType.boolean,
                DataType.text,
                DataType.email,
                DataType.name,
                DataType.address,
            }
            and self.distribution is not DistributionType.uniform
        ):
            raise ValueError(
                f"{self.type.value} attributes only support 'uniform' distribution"
            )

        return self


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None


class DatasetAttributesRequest(BaseModel):
    dataset_id: UUID
    attributes: list[AttributeConfig]
    seed: int | None = Field(default=None, ge=0)


class PreviewRequest(BaseModel):
    dataset_version_id: UUID
    seed: int | None = Field(default=None, ge=0)


class PreviewResponse(BaseModel):
    dataset_version_id: UUID
    rows: int
    data: list[dict[str, Any]]


class GenerateRequest(BaseModel):
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    row_count: int = Field(..., ge=1, le=10000000)
    formats: list[str] = Field(default_factory=lambda: ["csv"])
    seed: int | None = Field(default=None, ge=0)


class GeneratedFileInfo(BaseModel):
    format: str
    file_name: str
    size_bytes: int


class GenerateResponse(BaseModel):
    dataset_id: UUID
    status: str
    row_count: int
    files: list[GeneratedFileInfo]


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
