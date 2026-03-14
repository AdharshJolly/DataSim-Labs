"use client";

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
    const stored = localStorage.getItem("datasim:dataset_id");
    if (stored) {
      setDatasetId(stored);
    }
  }, []);

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Download</h1>
        <p className="text-muted-foreground">
          Download generated files in CSV, JSON, or Excel format.
        </p>
      </div>

      <div className="grid max-w-3xl gap-3 rounded-xl border bg-white/70 p-4">
        <label className="space-y-1 text-sm font-medium">
          Dataset ID
          <input
            className="w-full rounded-md border border-border bg-white px-3 py-2"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            placeholder="Paste dataset id"
          />
        </label>
        <button
          type="button"
          disabled={isLoading}
          onClick={loadFiles}
          className="w-fit rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {isLoading ? "Loading..." : "Load Files"}
        </button>
        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </div>

      {hasFiles ? (
        <div className="overflow-hidden rounded-xl border bg-white/70">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/60 text-left">
              <tr>
                <th className="px-3 py-2">Format</th>
                <th className="px-3 py-2">File</th>
                <th className="px-3 py-2">Size</th>
                <th className="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.file_name} className="border-t">
                  <td className="px-3 py-2 uppercase">{file.format}</td>
                  <td className="px-3 py-2">{file.file_name}</td>
                  <td className="px-3 py-2">
                    {file.size_bytes.toLocaleString()} bytes
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      className="rounded border px-3 py-1"
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
