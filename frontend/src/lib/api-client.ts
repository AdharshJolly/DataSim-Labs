export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
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

export interface CreateDatasetResponse {
  message: string;
  dataset_id: string;
  name: string;
}

export interface SaveAttributesRequest {
  dataset_id: string;
  attributes: AttributeConfig[];
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
  row_count: number;
  formats: Array<"csv" | "json" | "excel">;
}

export interface GeneratedFileInfo {
  format: string;
  file_name: string;
  file_path: string;
  size_bytes: number;
}

export interface GenerateResponse {
  dataset_id: string;
  status: string;
  row_count: number;
  files: GeneratedFileInfo[];
}

export interface DownloadListResponse {
  dataset_id: string;
  files: GeneratedFileInfo[];
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
): Promise<PreviewResponse> {
  return apiRequest<PreviewResponse>("/api/v1/dataset/preview", {
    method: "POST",
    body: JSON.stringify({ dataset_version_id: datasetVersionId }),
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
