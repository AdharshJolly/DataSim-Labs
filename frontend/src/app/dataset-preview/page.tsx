"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

import { previewDataset } from "@/lib/api-client";

type PreviewRow = Record<string, unknown>;

export default function DatasetPreviewPage() {
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [rows, setRows] = useState<PreviewRow[]>([]);
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const columns = useMemo<ColumnDef<PreviewRow>[]>(() => {
    const first = rows[0];
    if (!first) {
      return [];
    }
    return Object.keys(first).map((key) => ({
      accessorKey: key,
      header: key,
      cell: ({ getValue }) => String(getValue() ?? ""),
    }));
  }, [rows]);

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const onPreview = async () => {
    if (!datasetVersionId.trim()) {
      setStatus("Dataset version id is required.");
      return;
    }

    setIsLoading(true);
    setStatus("");
    try {
      const response = await previewDataset(datasetVersionId.trim());
      setRows(response.data);
      setStatus(`Loaded ${response.rows} preview rows.`);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Failed to load preview",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const storedDatasetId = localStorage.getItem("datasim:dataset_id");
    if (storedDatasetId) {
      setDatasetId(storedDatasetId);
    }
    const fromQuery = new URLSearchParams(window.location.search).get(
      "datasetVersionId",
    );
    if (fromQuery) {
      setDatasetVersionId(fromQuery);
      return;
    }
    const stored = localStorage.getItem("datasim:dataset_version_id");
    if (stored) {
      setDatasetVersionId(stored);
    }
  }, []);

  useEffect(() => {
    if (!datasetVersionId.trim()) {
      return;
    }
    void onPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetVersionId]);

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="font-[var(--font-title)] text-3xl font-bold">
          Dataset Preview
        </h1>
        <p className="text-muted-foreground">
          Quick sample check before full generation.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/dashboard" className="sk-btn sk-btn-muted">
          Back to Dashboard
        </Link>
        <Link
          href={`/generate-dataset?datasetId=${encodeURIComponent(datasetId)}&datasetVersionId=${encodeURIComponent(datasetVersionId)}`}
          className="sk-btn sk-btn-primary"
        >
          Continue to Generate
        </Link>
      </div>

      <div className="sk-panel max-w-3xl space-y-3">
        <label className="space-y-1 text-sm font-medium">
          Current Version
          <input
            className="sk-input"
            value={datasetVersionId}
            onChange={(e) => setDatasetVersionId(e.target.value)}
            placeholder="Automatically selected from your last saved version"
          />
        </label>
        <button
          type="button"
          disabled={isLoading}
          onClick={onPreview}
          className="sk-btn sk-btn-primary"
        >
          {isLoading ? "Loading..." : "Refresh Preview"}
        </button>
        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </div>

      <div className="sk-table-shell">
        <table className="sk-table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
