import { apiRequest } from "./core";
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
  return apiRequest<SemanticRulesResponse>(
    `/api/v1/rules/dataset/${datasetVersionId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
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
