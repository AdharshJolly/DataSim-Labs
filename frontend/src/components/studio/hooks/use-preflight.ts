import { useEffect } from "react";

import {
  generationPreflight,
  type GenerationPreflightResponse,
} from "@/lib/api-client";
import type { OutputFormat } from "@/lib/studio-constants";

interface UsePreflightArgs {
  enabled: boolean;
  datasetId: string;
  versionId: string;
  rowCount: number;
  formats: OutputFormat[];
  seed: string;
  driftEnabled: boolean;
  driftIntensity: number;
  driftColumnsText: string;
  setPreflightResult: (value: GenerationPreflightResponse | null) => void;
  setPreflightBusy: (value: boolean) => void;
}

export function usePreflight({
  enabled,
  datasetId,
  versionId,
  rowCount,
  formats,
  seed,
  driftEnabled,
  driftIntensity,
  driftColumnsText,
  setPreflightResult,
  setPreflightBusy,
}: UsePreflightArgs): void {
  useEffect(() => {
    if (!enabled || !datasetId || formats.length === 0) {
      return;
    }

    let isCancelled = false;
    setPreflightBusy(true);

    void generationPreflight({
      dataset_id: datasetId,
      dataset_version_id: versionId || undefined,
      row_count: rowCount,
      formats,
      seed: seed.trim() ? Number(seed) : undefined,
    })
      .then((response) => {
        if (!isCancelled) {
          setPreflightResult(response);
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setPreflightResult(null);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setPreflightBusy(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [
    enabled,
    datasetId,
    versionId,
    rowCount,
    formats,
    seed,
    driftEnabled,
    driftIntensity,
    driftColumnsText,
    setPreflightResult,
    setPreflightBusy,
  ]);
}
