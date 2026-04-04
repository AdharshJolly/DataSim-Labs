from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.attribute import AttributeConfig


class CorrelationRule(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    strength: float = Field(..., ge=-1.0, le=1.0)


class DatasetAttributesRequest(BaseModel):
    dataset_id: UUID
    attributes: list[AttributeConfig]
    seed: int | None = Field(default=None, ge=0)
    correlations: list[CorrelationRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_unique_names(self) -> "DatasetAttributesRequest":
        names = [attr.name for attr in self.attributes]
        dupes = [n for n in names if names.count(n) > 1]
        if dupes:
            raise ValueError(
                f"Duplicate attribute names: {', '.join(sorted(set(dupes)))}"
            )
        return self


class DatasetAttributesResponse(BaseModel):
    message: str
    dataset_id: UUID
    version_id: UUID
    version_number: int
    attribute_count: int


__all__ = [
    "AttributeConfig",
    "CorrelationRule",
    "DatasetAttributesRequest",
    "DatasetAttributesResponse",
]
