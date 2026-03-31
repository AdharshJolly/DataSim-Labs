import { API_BASE_URL, apiRequest, fetchWithAuth } from "./core";
import type {
  DryRunSemanticRulesRequest,
  DryRunSemanticRulesResponse,
  InferSemanticRulesRequest,
  InferSemanticRulesResponse,
  SemanticRulesResponse,
  UpsertSemanticRulesRequest,
} from "./types";

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
