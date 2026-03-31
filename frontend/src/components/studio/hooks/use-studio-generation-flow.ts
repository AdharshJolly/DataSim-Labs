import { useCallback } from "react";

import type { AttrRow, OutputFormat } from "@/components/studio/types";
import { validateCategoricalWeights } from "@/components/studio/helpers";
import {
  cancelGenerationJob,
  downloadDatasetFile,
  generateDataset,
  generateDatasetAsync,
  type GenerationJobStatus,
  getGenerationJob,
  streamDatasetCsv,
  submitDatasetFeedback,
} from "@/lib/api-client";

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

  const handleGenerate = useCallback(async () => {
    if (!datasetId) {
      setError("No dataset selected.");
      return;
    }
    if (formats.length === 0) {
      setError("Select at least one output format.");
      return;
    }

    setBusy(true);
    setError("");

    const weightError = attrs.map(validateCategoricalWeights).find(Boolean);
    if (weightError) {
      setBusy(false);
      setError(weightError);
      return;
    }

    try {
      const payload = {
        dataset_id: datasetId,
        dataset_version_id: versionId || undefined,
        row_count: rowCount,
        formats,
        seed: seed.trim() ? Number(seed) : undefined,
      };

      if (!shouldUseAsyncGeneration) {
        setAllowLowQualityDownloads(false);
        const result = await generateDataset(payload);
        applyGenerationResult(result as Record<string, any>);
        return;
      }

      const queued = await generateDatasetAsync(payload);
      setAllowLowQualityDownloads(false);
      setJobId(queued.job_id);
      setJobStatus(queued.status);
      setJobStage("queued");
      setJobProgress(0);

      const wait = (ms: number) =>
        new Promise((resolve) => setTimeout(resolve, ms));

      for (let attempt = 0; attempt < asyncPollMaxAttempts; attempt += 1) {
        const job = await getGenerationJob(queued.job_id);
        setJobStatus(job.status);
        setJobStage(job.stage);
        setJobProgress(job.progress_percentage);

        if (job.status === "completed") {
          const result = job.result;
          if (!result) {
            throw new Error(
              "Generation completed but no result payload returned.",
            );
          }
          applyGenerationResult(result as Record<string, any>);
          break;
        }

        if (job.status === "failed") {
          throw new Error(job.error || "Async generation job failed.");
        }

        if (job.status === "cancelled") {
          throw new Error("Async generation job was cancelled.");
        }

        await wait(asyncPollIntervalMs);

        if (attempt === asyncPollMaxAttempts - 1) {
          throw new Error("Timed out waiting for async generation job.");
        }
      }
    } catch (error) {
      notifyError("Generation Failed", error, "Generation failed");
    } finally {
      setBusy(false);
    }
  }, [
    datasetId,
    formats,
    setBusy,
    setError,
    attrs,
    versionId,
    rowCount,
    seed,
    shouldUseAsyncGeneration,
    setAllowLowQualityDownloads,
    applyGenerationResult,
    setJobId,
    setJobStatus,
    setJobStage,
    setJobProgress,
    asyncPollMaxAttempts,
    asyncPollIntervalMs,
    notifyError,
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

  const handleDownload = useCallback(
    async (format: string) => {
      try {
        const { blob, fileName } = await downloadDatasetFile(datasetId, format);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
      } catch (error) {
        notifyError("Download Failed", error, "Download failed");
      }
    },
    [datasetId, notifyError],
  );

  const handleStreamCsvDownload = useCallback(async () => {
    if (!versionId) {
      setError("No saved version to stream.");
      return;
    }

    setStreamingBusy(true);
    setStreamedBytes(0);
    setError("");
    try {
      const { blob, fileName } = await streamDatasetCsv(versionId, rowCount, {
        chunkSize: 50000,
        seed: seed.trim() ? Number(seed) : undefined,
        onProgressBytes: (bytesRead) => setStreamedBytes(bytesRead),
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      notifyError(
        "Streaming Download Failed",
        error,
        "Unable to stream CSV download.",
      );
    } finally {
      setStreamingBusy(false);
    }
  }, [
    versionId,
    setError,
    setStreamingBusy,
    setStreamedBytes,
    rowCount,
    seed,
    notifyError,
  ]);

  const handleSubmitFeedback = useCallback(async () => {
    if (!datasetId || feedbackRating < 1) {
      setError("Select a rating before submitting feedback.");
      return;
    }

    setFeedbackBusy(true);
    setError("");
    try {
      await submitDatasetFeedback({
        dataset_id: datasetId,
        dataset_version_id: versionId || undefined,
        rating: feedbackRating,
        comment: feedbackComment.trim() || undefined,
        generation_signature: generationSignature || undefined,
        config_snapshot: {
          row_count: rowCount,
          formats,
          attribute_count: attrs.length,
        },
      });
      pushToast({
        title: "Feedback Submitted",
        message: "Thanks! Your rating was recorded for adaptive tuning.",
        intent: "success",
      });
      setFeedbackComment("");
    } catch (error) {
      notifyError(
        "Feedback Failed",
        error,
        "Unable to submit feedback right now.",
      );
    } finally {
      setFeedbackBusy(false);
    }
  }, [
    datasetId,
    feedbackRating,
    setError,
    setFeedbackBusy,
    versionId,
    feedbackComment,
    generationSignature,
    rowCount,
    formats,
    attrs.length,
    pushToast,
    setFeedbackComment,
    notifyError,
  ]);

  return {
    handleGenerate,
    handleCancelJob,
    handleDownload,
    handleStreamCsvDownload,
    handleSubmitFeedback,
  };
}
