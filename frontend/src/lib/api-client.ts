export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function setAuthToken(token: string, refreshToken?: string): void {
  // Backward compatibility shim during migration to HttpOnly cookies.
  void token;
  void refreshToken;
}

export function clearAuthToken(): void {
  // Backward compatibility shim during migration to HttpOnly cookies.
}

async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      success?: boolean;
      error?:
        | string
        | {
            code?: string;
            message?: string;
            request_id?: string;
          };
      detail?: string | { message?: string };
      message?: string;
    };
    if (
      payload.success === false &&
      typeof payload.error === "object" &&
      payload.error?.message
    ) {
      const requestId = payload.error.request_id
        ? ` [request_id=${payload.error.request_id}]`
        : "";
      return `${payload.error.message}${requestId}`;
    }
    if (typeof payload.detail === "string") return payload.detail;
    if (typeof payload.detail === "object" && payload.detail?.message) {
      return payload.detail.message;
    }
    if (typeof payload.message === "string") return payload.message;
    if (typeof payload.error === "string") return payload.error;
  } catch {
    // Ignore parse failure and fallback to status text below.
  }
  return response.statusText || `HTTP ${response.status}`;
}

export interface TokenRefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

let refreshPromise: Promise<TokenRefreshResponse | null> | null = null;

function shouldRedirectToExpired(detail: string): boolean {
  const normalized = detail.toLowerCase();
  // Missing refresh token means unauthenticated user, not an expired session.
  if (normalized.includes("refresh token missing")) return false;
  if (normalized.includes("authentication required")) return false;
  return true;
}

function redirectToExpiredIfNeeded(): void {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  if (path.startsWith("/login") || path.startsWith("/register")) return;
  window.location.href = "/login?expired=true";
}

async function attemptRefresh(): Promise<TokenRefreshResponse | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
        credentials: "include",
        cache: "no-store",
      });

      if (!response.ok) {
        const detail = await parseApiError(response);
        if (shouldRedirectToExpired(detail)) {
          redirectToExpiredIfNeeded();
        }
        return null;
      }

      const data = (await response.json()) as TokenRefreshResponse;
      return data;
    } catch {
      redirectToExpiredIfNeeded();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function fetchWithAuth(
  url: string | URL,
  init?: RequestInit,
): Promise<Response> {
  const requestInit: RequestInit = {
    ...init,
    credentials: "include",
  };
  let response = await fetch(url, requestInit);

  // If unauthorized and we're not already trying to hit the auth endpoints
  const urlStr = url.toString();
  if (
    response.status === 401 &&
    !urlStr.includes("/api/v1/auth/refresh") &&
    !urlStr.includes("/api/v1/auth/login") &&
    !urlStr.includes("/api/v1/auth/register")
  ) {
    const newTokens = await attemptRefresh();
    if (newTokens) {
      // Retry after backend refresh updates HttpOnly cookies.
      response = await fetch(url, {
        ...init,
        credentials: "include",
      });
    }
  }

  return response;
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetchWithAuth(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await parseApiError(response);
    throw new Error(`${detail} (${response.status})`);
  }

  return (await response.json()) as T;
}

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

export function register(payload: AuthRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: AuthRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function me(): Promise<CurrentUserResponse> {
  return apiRequest<CurrentUserResponse>("/api/v1/auth/me");
}

export function logout(): Promise<{ message: string }> {
  return apiRequest<{ message: string }>("/api/v1/auth/logout", {
    method: "POST",
  });
}

export function createDataset(
  payload: CreateDatasetRequest,
): Promise<CreateDatasetResponse> {
  return apiRequest<CreateDatasetResponse>("/api/v1/dataset/create", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveAttributes(
  payload: SaveAttributesRequest,
): Promise<SaveAttributesResponse> {
  return apiRequest<SaveAttributesResponse>("/api/v1/dataset/attributes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function previewDataset(
  datasetVersionId: string,
  seed?: number,
): Promise<PreviewResponse> {
  return apiRequest<PreviewResponse>("/api/v1/dataset/preview", {
    method: "POST",
    body: JSON.stringify({ dataset_version_id: datasetVersionId, seed }),
  });
}

export function generateDataset(
  payload: GenerateRequest,
): Promise<GenerateResponse> {
  return apiRequest<GenerateResponse>("/api/v1/dataset/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generationPreflight(
  payload: GenerateRequest,
): Promise<GenerationPreflightResponse> {
  return apiRequest<GenerationPreflightResponse>("/api/v1/dataset/preflight", {
    method: "POST",
    body: JSON.stringify({
      dataset_id: payload.dataset_id,
      dataset_version_id: payload.dataset_version_id,
      row_count: payload.row_count,
      formats: payload.formats,
    }),
  });
}

export function generateDatasetAsync(
  payload: GenerateRequest,
): Promise<GenerateAsyncResponse> {
  return apiRequest<GenerateAsyncResponse>("/api/v1/dataset/generate-async", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getGenerationJob(
  jobId: string,
): Promise<GenerationJobResponse> {
  return apiRequest<GenerationJobResponse>(`/api/v1/dataset/jobs/${jobId}`);
}

export function cancelGenerationJob(
  jobId: string,
): Promise<CancelGenerationJobResponse> {
  return apiRequest<CancelGenerationJobResponse>(
    `/api/v1/dataset/jobs/${jobId}/cancel`,
    {
      method: "POST",
    },
  );
}

export function listGenerationJobs(
  limit = 20,
): Promise<GenerationJobListResponse> {
  return apiRequest<GenerationJobListResponse>(
    `/api/v1/dataset/jobs?limit=${encodeURIComponent(limit)}`,
  );
}

export function retryGenerationJob(
  jobId: string,
): Promise<RetryGenerationJobResponse> {
  return apiRequest<RetryGenerationJobResponse>(
    `/api/v1/dataset/jobs/${jobId}/retry`,
    {
      method: "POST",
    },
  );
}

export function listDatasetFiles(
  datasetId: string,
): Promise<DownloadListResponse> {
  return apiRequest<DownloadListResponse>(
    `/api/v1/dataset/download/${datasetId}`,
  );
}

export function buildDownloadUrl(datasetId: string, format: string): string {
  const search = new URLSearchParams({ format });
  return `${API_BASE_URL}/api/v1/dataset/download/${datasetId}?${search.toString()}`;
}

export async function downloadDatasetFile(
  datasetId: string,
  format: string,
): Promise<{ blob: Blob; fileName: string }> {
  const search = new URLSearchParams({ format });
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/dataset/download/${datasetId}?${search.toString()}`,
    {
      method: "GET",
    },
  );

  if (!response.ok) {
    const detail = await parseApiError(response);
    throw new Error(`${detail} (${response.status})`);
  }

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const match = contentDisposition.match(/filename="?([^";]+)"?/i);
  const fallback = `dataset_${datasetId}.${format === "excel" ? "xlsx" : format === "jsonl" ? "jsonl" : format}`;
  return {
    blob: await response.blob(),
    fileName: match?.[1] || fallback,
  };
}

export function listDatasets(): Promise<DatasetListResponse> {
  return apiRequest<DatasetListResponse>("/api/v1/dataset/list");
}

export function listDatasetTemplates(): Promise<DatasetTemplatesResponse> {
  return apiRequest<DatasetTemplatesResponse>("/api/v1/dataset/templates");
}

export function getDataset(datasetId: string): Promise<DatasetDetailResponse> {
  return apiRequest<DatasetDetailResponse>(`/api/v1/dataset/${datasetId}`);
}

export function getDatasetVersions(
  datasetId: string,
): Promise<DatasetVersionsResponse> {
  return apiRequest<DatasetVersionsResponse>(
    `/api/v1/dataset/${datasetId}/versions`,
  );
}

export function getSemanticRules(
  datasetVersionId: string,
): Promise<SemanticRulesResponse> {
  return apiRequest<SemanticRulesResponse>(
    `/api/v1/rules/dataset/${datasetVersionId}`,
  );
}

export function upsertSemanticRules(
  datasetVersionId: string,
  payload: UpsertSemanticRulesRequest,
): Promise<SemanticRulesResponse> {
  return fetchWithAuth(
    `${API_BASE_URL}/api/v1/rules/dataset/${datasetVersionId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      credentials: "include",
      cache: "no-store",
    },
  ).then(async (response) => {
    if (!response.ok) {
      let detail: unknown = null;
      try {
        const parsed = (await response.json()) as {
          detail?: unknown;
          message?: string;
        };
        detail = parsed.detail ?? parsed;
      } catch {
        detail = null;
      }

      const message = response.statusText || `HTTP ${response.status}`;
      const error = new Error(`${message} (${response.status})`) as Error & {
        detail?: unknown;
        status?: number;
      };
      error.detail = detail;
      error.status = response.status;
      throw error;
    }

    return (await response.json()) as SemanticRulesResponse;
  });
}

export function dryRunSemanticRules(
  datasetVersionId: string,
  payload: DryRunSemanticRulesRequest,
): Promise<DryRunSemanticRulesResponse> {
  return apiRequest<DryRunSemanticRulesResponse>(
    `/api/v1/rules/dataset/${datasetVersionId}/dry-run`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function inferSemanticRules(
  payload: InferSemanticRulesRequest,
): Promise<InferSemanticRulesResponse> {
  return apiRequest<InferSemanticRulesResponse>("/api/v1/rules/infer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteDataset(datasetId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/api/v1/dataset/${datasetId}`, {
    method: "DELETE",
  });
}
