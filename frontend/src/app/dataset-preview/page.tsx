"use client";

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

  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Dataset Preview</h1>
        <p className="text-muted-foreground">
          Render and inspect a 10-row generated sample.
        </p>
      </div>

      <div className="max-w-3xl space-y-3 rounded-xl border bg-white/70 p-4">
        <label className="space-y-1 text-sm font-medium">
          Dataset Version ID
          <input
            className="w-full rounded-md border border-border bg-white px-3 py-2"
            value={datasetVersionId}
            onChange={(e) => setDatasetVersionId(e.target.value)}
            placeholder="Paste dataset version id"
          />
        </label>
        <button
          type="button"
          disabled={isLoading}
          onClick={onPreview}
          className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {isLoading ? "Loading..." : "Generate Preview"}
        </button>
        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </div>

      <div className="overflow-x-auto rounded-xl border bg-white/70">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/60 text-left">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2 font-medium">
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
              <tr key={row.id} className="border-t">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2">
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
