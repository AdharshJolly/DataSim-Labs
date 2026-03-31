// API contract types - mirrors backend Pydantic schemas
export type DataType =
  | "integer"
  | "float"
  | "categorical"
  | "boolean"
  | "date"
  | "text"
  | "email"
  | "name"
  | "address";

export type DistributionType =
  | "uniform"
  | "normal"
  | "skewed"
  | "weighted_categorical";

export interface AttributeConfig {
  name: string;
  type: DataType;
  description: string;
  constraints: Record<string, unknown>;
  distribution: DistributionType;
  null_percentage: number;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  email: string;
}

export interface CurrentUserResponse {
  id: string;
  email: string;
  created_at: string;
}

export interface CreateDatasetResponse {
  message: string;
  dataset_id: string;
  name: string;
}

export interface SaveAttributesRequest {
  dataset_id: string;
  attributes: AttributeConfig[];
  seed?: number;
  correlations?: Array<{
    source: string;
    target: string;
    strength: number;
  }>;
}

export interface SaveAttributesResponse {
  message: string;
  dataset_id: string;
  version_id: string;
  version_number: number;
  attribute_count: number;
}

export interface PreviewResponse {
  dataset_version_id: string;
  rows: number;
  data: Record<string, unknown>[];
  comparison?: {
    columns: PreviewColumnComparison[];
  } | null;
}

export interface ExplainRequest {
  dataset_version_id: string;
  row_index?: number;
  seed?: number;
  column?: string;
}

export interface ExplainedCell {
  value: unknown;
  source: string;
  generator?: string | null;
  rule?: string | null;
  depends_on: string[];
}

export interface ExplainResponse {
  dataset_version_id: string;
  row_index: number;
  row: Record<string, unknown>;
  trace: Record<string, ExplainedCell>;
}

export interface AttributeSuggestion {
  attribute_name: string;
  suggested_distribution: DistributionType;
  suggested_constraints: Record<string, unknown>;
  confidence: number;
  reason: string;
}

export interface RelationshipSuggestion {
  source: string;
  target: string;
  strength: number;
  confidence: number;
  reason: string;
}

export interface SuggestionRequest {
  dataset_version_id?: string;
  attributes?: AttributeConfig[];
}

export interface SuggestionResponse {
  dataset_version_id?: string | null;
  attribute_suggestions: AttributeSuggestion[];
  relationship_suggestions: RelationshipSuggestion[];
  metadata: Record<string, unknown>;
}

export interface CompareRequest {
  dataset_version_id: string;
  generated_data: Record<string, unknown>[];
  seed?: number;
  sample_rows?: number;
}

export interface CompareMetric {
  column: string;
  mean_diff: number;
  variance_diff: number;
  kl_divergence: number;
  expected_mean: number;
  generated_mean: number;
  expected_variance: number;
  generated_variance: number;
}

export interface RefinementRecommendation {
  attribute_name: string;
  action: string;
  reason: string;
  suggested_distribution: DistributionType;
  confidence: number;
}

export interface CompareResponse {
  dataset_version_id: string;
  overall_drift_score: number;
  metrics: CompareMetric[];
  recommendations: RefinementRecommendation[];
}

export interface FeedbackRequest {
  dataset_id: string;
  dataset_version_id?: string;
  rating: number;
  comment?: string;
  generation_signature?: string;
  config_snapshot?: Record<string, unknown>;
}

export interface FeedbackResponse {
  feedback_id: string;
  dataset_id: string;
  dataset_version_id?: string | null;
  rating: number;
  comment?: string | null;
  message: string;
}

export interface FeedbackSummaryResponse {
  dataset_id?: string | null;
  count: number;
  average_rating?: number | null;
  ratings: number[];
  recent: Array<Record<string, unknown>>;
}

export interface PreviewHistogramBin {
  bin_start: number;
  bin_end: number;
  expected_count: number;
  synthetic_count: number;
}

export interface PreviewNumericComparison {
  expected_min?: number | null;
  expected_max?: number | null;
  expected_mean?: number | null;
  synthetic_min?: number | null;
  synthetic_max?: number | null;
  synthetic_mean?: number | null;
  expected_skewness?: number | null;
  synthetic_skewness?: number | null;
  expected_kurtosis?: number | null;
  synthetic_kurtosis?: number | null;
  ks_statistic?: number | null;
  ks_p_value?: number | null;
  ks_passed?: boolean | null;
  ad_statistic?: number | null;
  ad_significance_level?: number | null;
  ad_passed?: boolean | null;
  expected_missing_pct: number;
  synthetic_missing_pct: number;
  low_variance: boolean;
  histogram_bins: PreviewHistogramBin[];
}

export interface PreviewColumnComparison {
  column: string;
  data_type: string;
  distribution: string;
  numeric?: PreviewNumericComparison | null;
}

export interface GenerateRequest {
  dataset_id: string;
  dataset_version_id?: string;
  row_count: number;
  formats: Array<"csv" | "json" | "jsonl" | "excel">;
  seed?: number;
  enable_refinement?: boolean;
  max_refinement_iterations?: number;
}

export interface GenerationPreflightIssue {
  level: string;
  code: string;
  message: string;
}

export interface GenerationPreflightResponse {
  ok: boolean;
  requires_async: boolean;
  estimated_cells: number;
  estimated_output_bytes: number;
  issues: GenerationPreflightIssue[];
}

export interface GeneratedFileInfo {
  format: string;
  file_name: string;
  size_bytes: number;
}

export type DatasetStatus = "draft" | "active" | "generating" | "archived";

export interface ValidationSummary {
  realism_score: number | null;
  score?: number;
  status?: string;
  confidence: "high" | "medium" | "low" | "unknown";
  passed: boolean;
  warnings: Array<{
    severity: "warning" | "error";
    type: string;
    column?: string | null;
    message: string;
  }>;
  ks_tests?: Record<string, any> | null;
  kl_divergence?: Record<string, any> | null;
  correlation_error?: Record<string, any> | null;
  null_fidelity?: Record<string, any> | null;
  coherence_checks?: {
    name_email_coherence_score?: number;
    rows_checked?: number;
    rows_matched?: number;
  } | null;
}

export interface GenerateResponse {
  dataset_id: string;
  status: string;
  row_count: number;
  files: GeneratedFileInfo[];
  quality_report?: Record<string, unknown> | null;
  quality_dashboard?: {
    overall_score: number;
    metrics: {
      distribution_fidelity: number;
      relationship_integrity: number;
      null_pattern_match: number;
      uniqueness: number;
      freshness: number;
    };
    warnings: string[];
    recommendations: string[];
  } | null;
  validation_summary?: ValidationSummary | null;
  quality_guardrails?: {
    passed: boolean;
    max_alerts: number;
    actual_alerts: number;
    message: string;
  } | null;
  generation_signature?: string | null;
  generation_run_id?: string | null;
  comparison?: Record<string, unknown> | null;
  semantic_rule_metrics?: Record<string, unknown> | null;
}

export type GenerationJobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface GenerateAsyncResponse {
  job_id: string;
  status: GenerationJobStatus;
  message: string;
}

export interface GenerationJobResponse {
  job_id: string;
  dataset_id: string;
  dataset_version_id?: string | null;
  status: GenerationJobStatus;
  stage: string;
  progress_percentage: number;
  row_count: number;
  formats: string[];
  seed?: number | null;
  cancel_requested: boolean;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  result?: GenerateResponse | null;
}

export interface CancelGenerationJobResponse {
  job_id: string;
  status: GenerationJobStatus;
  cancel_requested: boolean;
  message: string;
}

export interface GenerationJobListResponse {
  jobs: GenerationJobResponse[];
}

export interface RetryGenerationJobResponse {
  original_job_id: string;
  new_job_id: string;
  status: GenerationJobStatus;
  message: string;
}

export interface DownloadListResponse {
  dataset_id: string;
  files: GeneratedFileInfo[];
}

export interface DatasetSummary {
  id: string;
  name: string;
  description?: string | null;
  latest_version_id?: string | null;
  status: DatasetStatus;
  created_at: string;
}

export interface DatasetVersionSummary {
  id: string;
  version_number: number;
  seed?: number | null;
  config_json: Record<string, unknown>;
  created_at: string;
}

export interface DatasetListResponse {
  datasets: DatasetSummary[];
}

export interface DatasetDetailResponse {
  id: string;
  name: string;
  description?: string | null;
  latest_version_id?: string | null;
  status: DatasetStatus;
  created_at: string;
  updated_at: string;
}

export interface DatasetVersionsResponse {
  dataset_id: string;
  versions: DatasetVersionSummary[];
}

export interface DatasetTemplate {
  id: string;
  name: string;
  description: string;
  columns?: Record<string, unknown>;
  dependency_graph?: unknown[];
  domain?: string;
  complexity?: "low" | "medium" | "high" | string;
  recommended_row_range?: {
    min: number;
    max: number;
  };
  tags?: string[];
  quality_targets?: Record<string, number>;
}

export interface DatasetTemplatesResponse {
  success: boolean;
  templates: DatasetTemplate[];
}

export interface SemanticRule {
  id: string;
  type: string;
  target: string;
  sources: string[];
  transform: Record<string, unknown>;
  confidence: number;
  priority: number;
  constraints?: Record<string, unknown> | null;
}

export type SemanticConflictPolicy = "priority_wins" | "last_write_wins";

export interface SemanticRulesMetadata {
  rule_count?: number;
  is_valid?: boolean;
  warnings?: string[];
  errors?: string[];
  conflict_policy?: SemanticConflictPolicy;
  execution_order?: string[];
  conflict_resolution?: Record<string, unknown>;
  updated?: boolean;
  source?: string;
  changed_rows?: number;
  changed_cells?: number;
}

export interface SemanticRulesResponse {
  dataset_version_id: string;
  rules: SemanticRule[];
  metadata: SemanticRulesMetadata;
}

export interface UpsertSemanticRulesRequest {
  rules: SemanticRule[];
  conflict_policy?: SemanticConflictPolicy;
}

export interface DryRunSemanticRulesRequest {
  rules: SemanticRule[];
  conflict_policy?: SemanticConflictPolicy;
  sample_rows?: number;
  seed?: number;
}

export interface DryRunSemanticRulesResponse {
  dataset_version_id: string;
  sample_rows: number;
  metadata: SemanticRulesMetadata;
  before: Record<string, unknown>[];
  after: Record<string, unknown>[];
  changed_cells: Array<{
    row: number;
    column: string;
    before: unknown;
    after: unknown;
  }>;
}

export interface InferSemanticRulesRequest {
  dataset_version_id?: string;
  sample_data?: Record<string, unknown>[];
  sample_rows?: number;
  max_rules?: number;
  min_confidence?: number;
  seed?: number;
  conflict_policy?: SemanticConflictPolicy;
}

export interface InferSemanticRulesResponse {
  dataset_version_id?: string | null;
  rules: SemanticRule[];
  metadata: SemanticRulesMetadata & {
    inference?: Record<string, unknown>;
    requested_rows?: number;
    used_rows?: number;
    returned_rule_count?: number;
    rule_count_before_validation?: number;
    min_confidence?: number;
  };
}
