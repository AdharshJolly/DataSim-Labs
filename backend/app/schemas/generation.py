from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PreviewRequest(BaseModel):
    dataset_version_id: UUID
    seed: int | None = Field(default=None, ge=0)


class PreviewHistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    expected_count: float
    synthetic_count: float


class PreviewNumericComparison(BaseModel):
    expected_min: float | None = None
    expected_max: float | None = None
    expected_mean: float | None = None
    synthetic_min: float | None = None
    synthetic_max: float | None = None
    synthetic_mean: float | None = None
    expected_skewness: float | None = None
    synthetic_skewness: float | None = None
    expected_kurtosis: float | None = None
    synthetic_kurtosis: float | None = None
    ks_statistic: float | None = None
    ks_p_value: float | None = None
    ks_passed: bool | None = None
    ad_statistic: float | None = None
    ad_significance_level: float | None = None
    ad_passed: bool | None = None
    expected_missing_pct: float
    synthetic_missing_pct: float
    low_variance: bool
    histogram_bins: list[PreviewHistogramBin] = Field(default_factory=list)


class PreviewColumnComparison(BaseModel):
    column: str
    data_type: str
    distribution: str
    numeric: PreviewNumericComparison | None = None


class PreviewComparisonPayload(BaseModel):
    columns: list[PreviewColumnComparison] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    dataset_version_id: UUID
    rows: int
    data: list[dict[str, Any]]
    comparison: PreviewComparisonPayload | None = None


class ExplainRequest(BaseModel):
    dataset_version_id: UUID
    row_index: int = Field(default=0, ge=0, le=999)
    seed: int | None = Field(default=None, ge=0)
    column: str | None = None


class ExplainedCell(BaseModel):
    value: Any
    source: str
    generator: str | None = None
    rule: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    dataset_version_id: UUID
    row_index: int
    row: dict[str, Any]
    trace: dict[str, ExplainedCell]


class AttributeSuggestion(BaseModel):
    attribute_name: str
    suggested_distribution: str
    suggested_constraints: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class RelationshipSuggestion(BaseModel):
    source: str
    target: str
    strength: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class SuggestionRequest(BaseModel):
    dataset_version_id: UUID | None = None
    attributes: list["AttributeConfig"] | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "SuggestionRequest":
        if self.dataset_version_id is None and not self.attributes:
            raise ValueError("Provide dataset_version_id or attributes for suggestions")
        return self


class SuggestionResponse(BaseModel):
    dataset_version_id: UUID | None = None
    attribute_suggestions: list[AttributeSuggestion] = Field(default_factory=list)
    relationship_suggestions: list[RelationshipSuggestion] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    dataset_version_id: UUID
    generated_data: list[dict[str, Any]] = Field(default_factory=list)
    seed: int | None = Field(default=None, ge=0)
    sample_rows: int = Field(default=100, ge=10, le=1000)


class CompareMetric(BaseModel):
    column: str
    mean_diff: float
    variance_diff: float
    kl_divergence: float
    expected_mean: float
    generated_mean: float
    expected_variance: float
    generated_variance: float


class RefinementRecommendation(BaseModel):
    attribute_name: str
    action: str
    reason: str
    suggested_distribution: str
    confidence: float = Field(ge=0.0, le=1.0)


class CompareResponse(BaseModel):
    dataset_version_id: UUID
    overall_drift_score: float
    metrics: list[CompareMetric] = Field(default_factory=list)
    recommendations: list[RefinementRecommendation] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    generation_signature: str | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    feedback_id: str
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    rating: int
    comment: str | None = None
    message: str


class FeedbackSummaryResponse(BaseModel):
    dataset_id: UUID | None = None
    count: int
    average_rating: float | None = None
    ratings: list[int] = Field(default_factory=list)
    recent: list[dict[str, Any]] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    row_count: int = Field(..., ge=1, le=10000000)
    formats: list[str] = Field(default_factory=lambda: ["csv"])
    seed: int | None = Field(default=None, ge=0)
    enable_refinement: bool = Field(
        default=False, description="Enable adaptive feedback refinement loop"
    )
    max_refinement_iterations: int = Field(default=3, ge=1, le=5)


class GenerationPreflightIssue(BaseModel):
    level: str
    code: str
    message: str


class GenerationPreflightRequest(BaseModel):
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    row_count: int = Field(..., ge=1, le=10000000)
    formats: list[str] = Field(default_factory=lambda: ["csv"])


class GenerationPreflightResponse(BaseModel):
    ok: bool
    requires_async: bool
    estimated_cells: int
    estimated_output_bytes: int
    issues: list[GenerationPreflightIssue]


class GeneratedFileInfo(BaseModel):
    format: str
    file_name: str
    size_bytes: int


class ValidationSummary(BaseModel):
    realism_score: int | None
    confidence: str
    passed: bool
    warnings: list[dict[str, Any]]
    ks_tests: dict[str, Any] | None = None
    kl_divergence: dict[str, Any] | None = None
    correlation_error: dict[str, Any] | None = None
    null_fidelity: dict[str, Any] | None = None


class GenerateResponse(BaseModel):
    dataset_id: UUID
    status: str
    row_count: int
    files: list[GeneratedFileInfo]
    quality_report: dict[str, Any] | None = None
    quality_dashboard: dict[str, Any] | None = None
    validation_summary: ValidationSummary | None = None
    quality_guardrails: dict[str, Any] | None = None
    generation_signature: str | None = None
    generation_run_id: str | None = None
    comparison: dict[str, Any] | None = None
    semantic_rule_metrics: dict[str, Any] | None = None


class DownloadListResponse(BaseModel):
    dataset_id: UUID
    files: list[GeneratedFileInfo]


from app.schemas.attribute import AttributeConfig

SuggestionRequest.model_rebuild()
