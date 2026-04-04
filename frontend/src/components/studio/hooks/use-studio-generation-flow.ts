import { useGenerationJobActions } from "./use-generation-job-actions";
import { useAsyncGeneration } from "./use-async-generation";
import { useDownloadActions } from "./use-download-actions";
import { useFeedbackActions } from "./use-feedback-actions";
import { useGenerationResultApplier } from "./use-generation-result-applier";
import { useJobPolling } from "./use-job-polling";
import { useSyncGeneration } from "./use-sync-generation";
import type { UseStudioGenerationFlowArgs } from "./use-studio-generation-flow.types";

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
  const applyGenerationResult = useGenerationResultApplier({
    setGeneratedFiles,
    setQualityReport,
    setQualityDashboard,
    setValidationSummary,
    setQualityGuardrails,
    setSemanticRuleMetrics,
    setGenerationSignature,
    setGenerationRunId,
    setRunComparison,
  });

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

  const { handleGenerate, handleCancelJob } = useGenerationJobActions({
    jobId,
    shouldUseAsyncGeneration,
    setBusy,
    setError,
    notifyError,
    runSyncGeneration,
    runAsyncGeneration,
    setJobStatus,
    setJobStage,
    setJobProgress,
  });

  return {
    handleGenerate,
    handleCancelJob,
    handleDownload,
    handleStreamCsvDownload,
    handleSubmitFeedback,
  };
}
