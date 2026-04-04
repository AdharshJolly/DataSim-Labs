import { useCallback } from "react";

import type { OutputFormat } from "@/components/studio/types";
import {
  generateDatasetAsync,
  type GenerationJobStatus,
} from "@/lib/api-client";

interface UseAsyncGenerationArgs {
  datasetId: string;
  versionId: string;
  rowCount: number;
  formats: OutputFormat[];
  seed: string;
  setJobId: (value: string) => void;
  setJobStatus: (value: GenerationJobStatus | "") => void;
  setJobStage: (value: string) => void;
  setJobProgress: (value: number) => void;
  setAllowLowQualityDownloads: (value: boolean) => void;
  pollQueuedJob: (queuedJobId: string) => Promise<void>;
}

export function useAsyncGeneration({
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
}: UseAsyncGenerationArgs) {
  const runAsyncGeneration = useCallback(async () => {
    const payload = {
      dataset_id: datasetId,
      dataset_version_id: versionId || undefined,
      row_count: rowCount,
      formats,
      seed: seed.trim() ? Number(seed) : undefined,
    };

    const queued = await generateDatasetAsync(payload);
    setAllowLowQualityDownloads(false);
    setJobId(queued.job_id);
    setJobStatus(queued.status);
    setJobStage("queued");
    setJobProgress(0);
    await pollQueuedJob(queued.job_id);
  }, [
    datasetId,
    versionId,
    rowCount,
    formats,
    seed,
    setAllowLowQualityDownloads,
    setJobId,
    setJobStatus,
    setJobStage,
    setJobProgress,
    pollQueuedJob,
  ]);

  return { runAsyncGeneration };
}
