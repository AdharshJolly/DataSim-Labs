from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


SemanticConflictPolicy = Literal["priority_wins", "keep_existing", "first_wins"]


class SemanticRule(BaseModel):
    id: str
    type: str
    target: str
    sources: list[str]
    transform: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = 1
    constraints: dict[str, Any] | None = None


class SemanticRulesMetadata(BaseModel):
    source: str | None = None
    conflict_policy: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class SemanticRulesResponse(BaseModel):
    dataset_version_id: UUID
    rules: list[SemanticRule] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertSemanticRulesRequest(BaseModel):
    rules: list[SemanticRule] = Field(default_factory=list)
    conflict_policy: str = Field(default="priority_wins")


class DryRunSemanticRulesRequest(BaseModel):
    rules: list[SemanticRule] = Field(default_factory=list)
    conflict_policy: str = Field(default="priority_wins")
    sample_rows: int = Field(default=10, ge=1, le=50)
    seed: int | None = Field(default=None, ge=0)


class DryRunSemanticRulesResponse(BaseModel):
    dataset_version_id: UUID
    sample_rows: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    before: list[dict[str, Any]] = Field(default_factory=list)
    after: list[dict[str, Any]] = Field(default_factory=list)
    changed_cells: list[dict[str, Any]] = Field(default_factory=list)


class InferSemanticRulesRequest(BaseModel):
    dataset_version_id: UUID | None = None
    sample_data: list[dict[str, Any]] | None = None
    sample_rows: int = Field(default=50, ge=5, le=500)
    max_rules: int = Field(default=20, ge=1, le=100)
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    seed: int | None = Field(default=None, ge=0)
    conflict_policy: str = Field(default="priority_wins")


class InferSemanticRulesResponse(BaseModel):
    dataset_version_id: UUID | None = None
    rules: list[SemanticRule] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
