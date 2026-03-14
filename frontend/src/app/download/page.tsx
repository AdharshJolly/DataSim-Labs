"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  GeneratedFileInfo,
  downloadDatasetFile,
  listDatasetFiles,
} from "@/lib/api-client";

export default function DownloadPage() {
  const [datasetId, setDatasetId] = useState("");
  const [files, setFiles] = useState<GeneratedFileInfo[]>([]);
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const hasFiles = useMemo(() => files.length > 0, [files.length]);

  const loadFiles = async () => {
    if (!datasetId.trim()) {
      setStatus("Dataset id is required.");
      return;
    }

    setIsLoading(true);
    setStatus("");
    try {
      const response = await listDatasetFiles(datasetId.trim());
      setFiles(response.files);
      setStatus(`Found ${response.files.length} generated files.`);
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Failed to fetch generated files",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const onDownload = async (format: string) => {
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
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Download failed");
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const datasetFromQuery = params.get("datasetId");
    if (datasetFromQuery) {
      setDatasetId(datasetFromQuery);
      return;
    }
    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored) {
      setDatasetId(stored);
    }
  }, []);

  useEffect(() => {
    if (!datasetId.trim()) {
      return;
    }
    void loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="font-[var(--font-title)] text-3xl font-bold">
          Download
        </h1>
        <p className="text-muted-foreground">
          Your generated files are loaded automatically.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/dashboard" className="sk-btn sk-btn-muted">
          Back to Dashboard
        </Link>
      </div>

      <div className="sk-panel grid max-w-3xl gap-3">
        <label className="space-y-1 text-sm font-medium">
          Current Dataset
          <input
            className="sk-input"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            placeholder="Automatically selected from your last generation"
          />
        </label>
        <button
          type="button"
          disabled={isLoading}
          onClick={loadFiles}
          className="sk-btn sk-btn-primary w-fit"
        >
          {isLoading ? "Loading..." : "Refresh Files"}
        </button>
        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </div>

      {hasFiles ? (
        <div className="sk-table-shell">
          <table className="sk-table">
            <thead>
              <tr>
                <th>Format</th>
                <th>File</th>
                <th>Size</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.file_name}>
                  <td className="uppercase">
                    <span className="sk-chip">{file.format}</span>
                  </td>
                  <td>{file.file_name}</td>
                  <td>{file.size_bytes.toLocaleString()} bytes</td>
                  <td>
                    <button
                      type="button"
                      className="sk-btn sk-btn-muted px-3 py-1.5"
                      onClick={() => void onDownload(file.format)}
                    >
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
