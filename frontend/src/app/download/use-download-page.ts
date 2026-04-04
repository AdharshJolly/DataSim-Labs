"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  type GeneratedFileInfo,
  downloadDatasetFile,
  listDatasetFiles,
  type ValidationSummary,
} from "@/lib/api-client";
import {
  getStoredDatasetId,
  getStoredValidationSummary,
} from "@/lib/local-storage";
import { useErrorNotifier } from "@/lib/use-error-notifier";

export function useDownloadPage() {
  const [datasetId, setDatasetId] = useState("");
  const [files, setFiles] = useState<GeneratedFileInfo[]>([]);
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [validationSummary, setValidationSummary] =
    useState<ValidationSummary | null>(null);
  const [allowLowQualityDownloads, setAllowLowQualityDownloads] =
    useState(false);
  const { notifyError } = useErrorNotifier(setError);

  const hasFiles = useMemo(() => files.length > 0, [files.length]);
  const validationPassed = validationSummary?.passed ?? true;

  const loadFiles = useCallback(async () => {
    if (!datasetId.trim()) {
      return;
    }

    setIsLoading(true);
    setStatus("");
    setError("");
    try {
      const response = await listDatasetFiles(datasetId.trim());
      setFiles(response.files);
      if (response.files.length === 0) {
        setStatus("No files generated for this dataset yet.");
      }
    } catch (err) {
      notifyError("Load Files Failed", err, "Failed to fetch generated files");
    } finally {
      setIsLoading(false);
    }
  }, [datasetId, notifyError]);

  const onDownload = useCallback(
    async (format: string) => {
      try {
        const { blob, fileName } = await downloadDatasetFile(
          datasetId.trim(),
          format,
        );
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
      } catch (err) {
        notifyError("Download Failed", err, "Download failed");
      }
    },
    [datasetId, notifyError],
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const datasetFromQuery = params.get("datasetId");
    if (datasetFromQuery) {
      setDatasetId(datasetFromQuery);
      return;
    }

    const stored = getStoredDatasetId();
    if (stored) {
      setDatasetId(stored);
    }
    setValidationSummary(getStoredValidationSummary());
  }, []);

  useEffect(() => {
    if (!datasetId.trim()) {
      return;
    }
    void loadFiles();
  }, [datasetId, loadFiles]);

  return {
    datasetId,
    setDatasetId,
    files,
    status,
    isLoading,
    error,
    validationSummary,
    allowLowQualityDownloads,
    setAllowLowQualityDownloads,
    hasFiles,
    validationPassed,
    loadFiles,
    onDownload,
  };
}
