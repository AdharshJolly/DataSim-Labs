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
      detail?: string | { message?: string };
      message?: string;
      error?: string;
    };
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
}

export interface GenerateRequest {
  dataset_id: string;
  dataset_version_id?: string;
  row_count: number;
  formats: Array<"csv" | "json" | "jsonl" | "excel">;
  seed?: number;
  drift_profile?: {
    enabled: boolean;
    intensity: number;
    target_columns: string[];
  };
  enable_refinement?: boolean;
  max_refinement_iterations?: number;
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
}

export interface GenerateResponse {
  dataset_id: string;
  status: string;
  row_count: number;
  files: GeneratedFileInfo[];
  quality_report?: Record<string, unknown> | null;
  validation_summary?: ValidationSummary | null;
  quality_guardrails?: {
    passed: boolean;
    max_alerts: number;
    actual_alerts: number;
    message: string;
  } | null;
  drift_simulation?: Record<string, unknown> | null;
  generation_signature?: string | null;
  generation_run_id?: string | null;
  comparison?: Record<string, unknown> | null;
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

export interface ProfileColumnDistribution {
  type?: string;
  semantic_type?: string;
  generator?: string;
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
}

export interface ProfileColumn {
  data_type: string;
  semantic_type?: string | null;
  unique_ratio?: number;
  confidence?: number;
  null_percentage: number;
  distribution?: ProfileColumnDistribution;
}

export interface ProfileDependency {
  source?: string;
  target?: string;
  sources?: string[];
  columns?: string[];
  type: string;
  correlation?: number;
  strength?: number;
}

export interface DatasetProfile {
  row_count: number;
  columns: Record<string, ProfileColumn>;
  dependency_graph?: ProfileDependency[];
  metadata?: {
    row_count?: number;
    confidence_score?: number;
    low_confidence?: boolean;
  };
  explainability?: {
    columns?: Record<
      string,
      {
        type?: string;
        distribution?: string;
        mean?: number;
        std?: number;
        min?: number;
        max?: number;
        confidence?: number;
      }
    >;
    correlations?: Array<Record<string, unknown>>;
    meta?: {
      rows_analyzed?: number;
      confidence?: string;
      confidence_score?: number;
      low_confidence?: boolean;
    };
  };
}

export interface UploadProfileResponse {
  message: string;
  profile: DatasetProfile;
}

export interface GenerateFromProfileRequest {
  row_count: number;
  seed?: number;
  enable_feedback_loop?: boolean;
  max_iterations?: number;
}

export interface GenerateFromProfileResponse {
  dataset_version_id: string;
  rows: number;
  data: Record<string, unknown>[];
  validation_summary?: ValidationSummary;
  generation_metadata?: Record<string, unknown>;
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

export async function uploadDatasetProfile(
  datasetVersionId: string,
  file: File,
): Promise<UploadProfileResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/dataset/${encodeURIComponent(datasetVersionId)}/profile/upload`,
    {
      method: "POST",
      body: formData,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const detail = await parseApiError(response);
    throw new Error(`${detail} (${response.status})`);
  }

  return (await response.json()) as UploadProfileResponse;
}

export function getDatasetProfile(
  datasetVersionId: string,
): Promise<DatasetProfile> {
  return apiRequest<DatasetProfile>(
    `/api/v1/dataset/${encodeURIComponent(datasetVersionId)}/profile`,
  );
}

export function generateDataFromProfile(
  datasetVersionId: string,
  payload: GenerateFromProfileRequest,
): Promise<GenerateFromProfileResponse> {
  const search = new URLSearchParams();
  search.set("row_count", String(payload.row_count));
  if (typeof payload.seed === "number") {
    search.set("seed", String(payload.seed));
  }
  search.set(
    "enable_feedback_loop",
    String(payload.enable_feedback_loop ?? true),
  );
  search.set("max_iterations", String(payload.max_iterations ?? 3));

  return apiRequest<GenerateFromProfileResponse>(
    `/api/v1/dataset/${encodeURIComponent(datasetVersionId)}/profile/generate?${search.toString()}`,
    {
      method: "POST",
    },
  );
}

export function deleteDataset(datasetId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/api/v1/dataset/${datasetId}`, {
    method: "DELETE",
  });
}
