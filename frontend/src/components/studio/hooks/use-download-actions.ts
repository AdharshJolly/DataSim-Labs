import { useCallback } from "react";

import { downloadDatasetFile, streamDatasetCsv } from "@/lib/api-client";

interface UseDownloadActionsArgs {
  datasetId: string;
  versionId: string;
  rowCount: number;
  seed: string;
  setError: (value: string) => void;
  setStreamingBusy: (value: boolean) => void;
  setStreamedBytes: (value: number) => void;
  notifyError: (title: string, error: unknown, fallback: string) => void;
}

export function useDownloadActions({
  datasetId,
  versionId,
  rowCount,
  seed,
  setError,
  setStreamingBusy,
  setStreamedBytes,
  notifyError,
}: UseDownloadActionsArgs) {
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

  return { handleDownload, handleStreamCsvDownload };
}
