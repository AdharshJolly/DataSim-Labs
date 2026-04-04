import { useCallback } from "react";

import { setStoredValidationSummary } from "@/lib/local-storage";

interface UseGenerationResultApplierArgs {
  setGeneratedFiles: (value: any[]) => void;
  setQualityReport: (value: Record<string, unknown> | null) => void;
  setQualityDashboard: (value: any) => void;
  setValidationSummary: (value: any) => void;
  setQualityGuardrails: (value: Record<string, unknown> | null) => void;
  setSemanticRuleMetrics: (value: Record<string, unknown> | null) => void;
  setGenerationSignature: (value: string) => void;
  setGenerationRunId: (value: string) => void;
  setRunComparison: (value: Record<string, unknown> | null) => void;
}

export function useGenerationResultApplier({
  setGeneratedFiles,
  setQualityReport,
  setQualityDashboard,
  setValidationSummary,
  setQualityGuardrails,
  setSemanticRuleMetrics,
  setGenerationSignature,
  setGenerationRunId,
  setRunComparison,
}: UseGenerationResultApplierArgs) {
  return useCallback(
    (result: Record<string, any>) => {
      setGeneratedFiles(result.files ?? []);
      setQualityReport(
        (result.quality_report as Record<string, unknown>) ?? null,
      );
      setQualityDashboard(result.quality_dashboard ?? null);
      setValidationSummary(result.validation_summary ?? null);
      if (result.validation_summary) {
        try {
          setStoredValidationSummary(result.validation_summary);
        } catch {
          // Ignore localStorage failures.
        }
      }
      setQualityGuardrails(
        (result.quality_guardrails as Record<string, unknown>) ?? null,
      );
      setSemanticRuleMetrics(
        (result.semantic_rule_metrics as Record<string, unknown>) ?? null,
      );
      setGenerationSignature(result.generation_signature ?? "");
      setGenerationRunId(result.generation_run_id ?? "");
      setRunComparison((result.comparison as Record<string, unknown>) ?? null);
    },
    [
      setGeneratedFiles,
      setQualityReport,
      setQualityDashboard,
      setValidationSummary,
      setQualityGuardrails,
      setSemanticRuleMetrics,
      setGenerationSignature,
      setGenerationRunId,
      setRunComparison,
    ],
  );
}
