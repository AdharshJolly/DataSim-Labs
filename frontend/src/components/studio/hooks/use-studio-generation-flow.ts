import { useCallback } from "react";

import type { AttrRow, OutputFormat } from "@/components/studio/types";
import {
  cancelGenerationJob,
  type GenerationJobStatus,
} from "@/lib/api-client";
import { useAsyncGeneration } from "./use-async-generation";
import { useDownloadActions } from "./use-download-actions";
import { useFeedbackActions } from "./use-feedback-actions";
import { useJobPolling } from "./use-job-polling";
import { useSyncGeneration } from "./use-sync-generation";

interface ToastInput {
  title: string;
  message: string;
  intent?: "success" | "info" | "error";
  durationMs?: number;
}

interface UseStudioGenerationFlowArgs {
  datasetId: string;
  versionId: string;
  attrs: AttrRow[];
  formats: OutputFormat[];
  rowCount: number;
  seed: string;
  shouldUseAsyncGeneration: boolean;
  feedbackRating: number;
  feedbackComment: string;
  generationSignature: string;
  jobId: string;
  setError: (value: string) => void;
  setBusy: (value: boolean) => void;
  setStreamingBusy: (value: boolean) => void;
  setStreamedBytes: (value: number) => void;
  setFeedbackBusy: (value: boolean) => void;
  setFeedbackComment: (value: string) => void;
  setAllowLowQualityDownloads: (value: boolean) => void;
  setGeneratedFiles: (value: any[]) => void;
  setQualityReport: (value: Record<string, unknown> | null) => void;
  setQualityDashboard: (value: any) => void;
  setValidationSummary: (value: any) => void;
  setQualityGuardrails: (value: Record<string, unknown> | null) => void;
  setSemanticRuleMetrics: (value: Record<string, unknown> | null) => void;
  setGenerationSignature: (value: string) => void;
  setGenerationRunId: (value: string) => void;
  setRunComparison: (value: Record<string, unknown> | null) => void;
  setJobId: (value: string) => void;
  setJobStatus: (value: GenerationJobStatus | "") => void;
  setJobStage: (value: string) => void;
  setJobProgress: (value: number) => void;
  notifyError: (title: string, error: unknown, fallback: string) => void;
  pushToast: (toast: ToastInput) => void;
  asyncPollIntervalMs: number;
  asyncPollMaxAttempts: number;
}

export function useStudioGenerationFlow({
  datasetId,
  versionId,
  attrs,
  formats,
  rowCount,
  seed,
  shouldUseAsyncGeneration,
  feedbackRating,
  feedbackComment,
  generationSignature,
  jobId,
  setError,
  setBusy,
  setStreamingBusy,
  setStreamedBytes,
  setFeedbackBusy,
  setFeedbackComment,
  setAllowLowQualityDownloads,
  setGeneratedFiles,
  setQualityReport,
  setQualityDashboard,
  setValidationSummary,
  setQualityGuardrails,
  setSemanticRuleMetrics,
  setGenerationSignature,
  setGenerationRunId,
  setRunComparison,
  setJobId,
  setJobStatus,
  setJobStage,
  setJobProgress,
  notifyError,
  pushToast,
  asyncPollIntervalMs,
  asyncPollMaxAttempts,
}: UseStudioGenerationFlowArgs) {
  const applyGenerationResult = useCallback(
    (result: Record<string, any>) => {
      setGeneratedFiles(result.files ?? []);
      setQualityReport(
        (result.quality_report as Record<string, unknown>) ?? null,
      );
      setQualityDashboard(result.quality_dashboard ?? null);
      setValidationSummary(result.validation_summary ?? null);
      if (result.validation_summary) {
        try {
          localStorage.setItem(
            "datasim:validation_summary",
            JSON.stringify(result.validation_summary),
          );
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

  const runSyncGeneration = useSyncGeneration({
    datasetId,
    versionId,
    attrs,
    formats,
    rowCount,
    seed,
    setError,
    setAllowLowQualityDownloads,
    applyGenerationResult,
  });

  const pollQueuedJob = useJobPolling({
    asyncPollIntervalMs,
    asyncPollMaxAttempts,
    setJobStatus,
    setJobStage,
    setJobProgress,
    applyGenerationResult,
  });

  const { runAsyncGeneration } = useAsyncGeneration({
    datasetId,
    versionId,
    rowCount,
    formats,
    seed,
    setJobId,
    setJobStatus,
    setJobStage,
    setJobProgress,
    setAllowLowQualityDownloads,
    pollQueuedJob,
  });

  const { handleDownload, handleStreamCsvDownload } = useDownloadActions({
    datasetId,
    versionId,
    rowCount,
    seed,
    setError,
    setStreamingBusy,
    setStreamedBytes,
    notifyError,
  });

  const { handleSubmitFeedback } = useFeedbackActions({
    datasetId,
    versionId,
    rowCount,
    formats,
    attrs,
    feedbackRating,
    feedbackComment,
    generationSignature,
    setError,
    setFeedbackBusy,
    setFeedbackComment,
    pushToast,
    notifyError,
  });

  const handleGenerate = useCallback(async () => {
    setBusy(true);
    setError("");

    try {
      if (!shouldUseAsyncGeneration) {
        await runSyncGeneration();
        return;
      }
      await runAsyncGeneration();
    } catch (error) {
      notifyError("Generation Failed", error, "Generation failed");
    } finally {
      setBusy(false);
    }
  }, [
    setBusy,
    setError,
    shouldUseAsyncGeneration,
    notifyError,
    runSyncGeneration,
    runAsyncGeneration,
  ]);

  const handleCancelJob = useCallback(async () => {
    if (!jobId) {
      return;
    }
    try {
      const result = await cancelGenerationJob(jobId);
      setJobStatus(result.status);
      setJobStage("cancel_requested");
      if (result.status === "cancelled") {
        setJobProgress(100);
      }
    } catch (error) {
      notifyError("Cancel Job Failed", error, "Failed to cancel job");
    }
  }, [jobId, setJobStatus, setJobStage, setJobProgress, notifyError]);

  return {
    handleGenerate,
    handleCancelJob,
    handleDownload,
    handleStreamCsvDownload,
    handleSubmitFeedback,
  };
}
