import { useCallback } from "react";

import type { AttrRow, OutputFormat } from "@/components/studio/types";
import { validateCategoricalWeights } from "@/components/studio/studio-helpers";
import { generateDataset, type GenerateRequest } from "@/lib/api-client";

interface UseSyncGenerationArgs {
  datasetId: string;
  versionId: string;
  attrs: AttrRow[];
  formats: OutputFormat[];
  rowCount: number;
  seed: string;
  setError: (value: string) => void;
  setAllowLowQualityDownloads: (value: boolean) => void;
  applyGenerationResult: (result: Record<string, unknown>) => void;
}

export function useSyncGeneration({
  datasetId,
  versionId,
  attrs,
  formats,
  rowCount,
  seed,
  setError,
  setAllowLowQualityDownloads,
  applyGenerationResult,
}: UseSyncGenerationArgs) {
  return useCallback(async () => {
    if (!datasetId) {
      setError("No dataset selected.");
      return;
    }

    if (formats.length === 0) {
      setError("Select at least one output format.");
      return;
    }

    const weightError = attrs.map(validateCategoricalWeights).find(Boolean);
    if (weightError) {
      setError(weightError);
      return;
    }

    const payload: GenerateRequest = {
      dataset_id: datasetId,
      dataset_version_id: versionId || undefined,
      row_count: rowCount,
      formats,
      seed: seed.trim() ? Number(seed) : undefined,
    };

    setAllowLowQualityDownloads(false);
    const result = await generateDataset(payload);
    applyGenerationResult(result as unknown as Record<string, unknown>);
  }, [
    datasetId,
    versionId,
    attrs,
    formats,
    rowCount,
    seed,
    setError,
    setAllowLowQualityDownloads,
    applyGenerationResult,
  ]);
}
