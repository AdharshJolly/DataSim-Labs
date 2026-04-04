import { useCallback } from "react";

import { cancelGenerationJob } from "@/lib/api-client";

interface UseGenerationJobActionsArgs {
  jobId: string;
  shouldUseAsyncGeneration: boolean;
  setBusy: (value: boolean) => void;
  setError: (value: string) => void;
  notifyError: (title: string, error: unknown, fallback: string) => void;
  runSyncGeneration: () => Promise<void>;
  runAsyncGeneration: () => Promise<void>;
  setJobStatus: (value: any) => void;
  setJobStage: (value: string) => void;
  setJobProgress: (value: number) => void;
}

export function useGenerationJobActions({
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
}: UseGenerationJobActionsArgs) {
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

  return { handleGenerate, handleCancelJob };
}
