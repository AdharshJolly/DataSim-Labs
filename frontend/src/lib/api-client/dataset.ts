import { apiRequest } from "./core";
import type {
  CompareRequest,
  CompareResponse,
  CreateDatasetRequest,
  CreateDatasetResponse,
  ExplainRequest,
  ExplainResponse,
  FeedbackRequest,
  FeedbackResponse,
  FeedbackSummaryResponse,
  GenerateAsyncResponse,
  GenerateRequest,
  GenerateResponse,
  GenerationJobListResponse,
  GenerationJobResponse,
  GenerationPreflightResponse,
  RetryGenerationJobResponse,
  SaveAttributesRequest,
  SaveAttributesResponse,
  SuggestionRequest,
  SuggestionResponse,
  PreviewResponse,
  CancelGenerationJobResponse,
  DatasetListResponse,
  DatasetDetailResponse,
  DatasetVersionsResponse,
  DatasetTemplatesResponse,
} from "./types";

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

export function explainDatasetRow(
  payload: ExplainRequest,
): Promise<ExplainResponse> {
  return apiRequest<ExplainResponse>("/api/v1/dataset/explain", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function suggestDatasetSettings(
  payload: SuggestionRequest,
): Promise<SuggestionResponse> {
  return apiRequest<SuggestionResponse>("/api/v1/dataset/suggestions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function compareDatasetOutput(
  payload: CompareRequest,
): Promise<CompareResponse> {
  return apiRequest<CompareResponse>("/api/v1/dataset/compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitDatasetFeedback(
  payload: FeedbackRequest,
): Promise<FeedbackResponse> {
  return apiRequest<FeedbackResponse>("/api/v1/dataset/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFeedbackSummary(
  datasetId?: string,
): Promise<FeedbackSummaryResponse> {
  const search = new URLSearchParams();
  if (datasetId) {
    search.set("dataset_id", datasetId);
  }
  const query = search.toString();
  return apiRequest<FeedbackSummaryResponse>(
    `/api/v1/dataset/feedback-summary${query ? `?${query}` : ""}`,
  );
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

export function deleteDataset(datasetId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/api/v1/dataset/${datasetId}`, {
    method: "DELETE",
  });
}
