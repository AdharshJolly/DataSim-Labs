"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  DatasetSummary,
  clearAuthToken,
  deleteDataset,
  listDatasets,
  me,
} from "@/lib/api-client";

export default function DashboardPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");

  const loadData = async () => {
    try {
      const [profile, datasetResponse] = await Promise.all([
        me(),
        listDatasets(),
      ]);
      setEmail(profile.email);
      setDatasets(datasetResponse.datasets);
      setStatus("");
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Failed to load dashboard data",
      );
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const onDelete = async (datasetId: string) => {
    try {
      await deleteDataset(datasetId);
      await loadData();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Delete failed");
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground">Signed in as {email || "-"}</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/create-dataset"
            className="rounded-md border px-3 py-2 text-sm"
          >
            New Dataset
          </Link>
          <button
            type="button"
            className="rounded-md border px-3 py-2 text-sm"
            onClick={() => {
              clearAuthToken();
              window.location.href = "/login";
            }}
          >
            Logout
          </button>
        </div>
      </div>

      {status ? (
        <p className="text-sm text-muted-foreground">{status}</p>
      ) : null}

      <div className="overflow-hidden rounded-xl border bg-white/70">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/60 text-left">
            <tr>
              <th className="px-3 py-2">Dataset</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2">Latest Version</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((dataset) => (
              <tr key={dataset.id} className="border-t">
                <td className="px-3 py-2">
                  <div className="font-medium">{dataset.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {dataset.description || "-"}
                  </div>
                </td>
                <td className="px-3 py-2">
                  {new Date(dataset.created_at).toLocaleString()}
                </td>
                <td className="px-3 py-2">
                  {dataset.latest_version_id || "-"}
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-2">
                    <Link
                      href={`/attribute-builder?datasetId=${dataset.id}`}
                      className="rounded border px-2 py-1"
                    >
                      Edit
                    </Link>
                    <Link
                      href={`/dataset-preview?datasetVersionId=${dataset.latest_version_id ?? ""}`}
                      className="rounded border px-2 py-1"
                    >
                      Preview
                    </Link>
                    <Link
                      href={`/generate-dataset?datasetId=${dataset.id}&datasetVersionId=${dataset.latest_version_id ?? ""}`}
                      className="rounded border px-2 py-1"
                    >
                      Generate
                    </Link>
                    <button
                      type="button"
                      className="rounded border px-2 py-1"
                      onClick={() => void onDelete(dataset.id)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
