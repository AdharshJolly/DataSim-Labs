import { useCallback } from "react";

import {
  getGenerationJob,
  type GenerationJobResponse,
  type GenerationJobStatus,
} from "@/lib/api-client";

interface UseJobPollingArgs {
  asyncPollIntervalMs: number;
  asyncPollMaxAttempts: number;
  setJobStatus: (value: GenerationJobStatus | "") => void;
  setJobStage: (value: string) => void;
  setJobProgress: (value: number) => void;
  applyGenerationResult: (result: Record<string, unknown>) => void;
}

export function useJobPolling({
  asyncPollIntervalMs,
  asyncPollMaxAttempts,
  setJobStatus,
  setJobStage,
  setJobProgress,
  applyGenerationResult,
}: UseJobPollingArgs) {
  return useCallback(
    async (queuedJobId: string) => {
      const wait = (ms: number) =>
        new Promise((resolve) => setTimeout(resolve, ms));

      for (let attempt = 0; attempt < asyncPollMaxAttempts; attempt += 1) {
        const job: GenerationJobResponse = await getGenerationJob(queuedJobId);
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
          applyGenerationResult(result as unknown as Record<string, unknown>);
          return;
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
    },
    [
      asyncPollIntervalMs,
      asyncPollMaxAttempts,
      setJobStatus,
      setJobStage,
      setJobProgress,
      applyGenerationResult,
    ],
  );
}
