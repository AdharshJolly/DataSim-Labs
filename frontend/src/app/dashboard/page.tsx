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
          <h1 className="font-[var(--font-title)] text-3xl font-bold">
            Dashboard
          </h1>
          <p className="text-muted-foreground">Signed in as {email || "-"}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/create-dataset" className="sk-btn sk-btn-muted">
            New Dataset
          </Link>
          <button
            type="button"
            className="sk-btn sk-btn-muted"
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

      <div className="sk-table-shell">
        <table className="sk-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Created</th>
              <th>Latest Version</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((dataset) => (
              <tr key={dataset.id}>
                <td>
                  <div className="font-medium">{dataset.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {dataset.description || "-"}
                  </div>
                </td>
                <td>{new Date(dataset.created_at).toLocaleString()}</td>
                <td>
                  <span className="sk-chip">
                    {dataset.latest_version_id || "-"}
                  </span>
                </td>
                <td>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      href={`/attribute-builder?datasetId=${dataset.id}`}
                      className="sk-btn sk-btn-muted px-3 py-1.5"
                    >
                      Edit
                    </Link>
                    <Link
                      href={`/dataset-preview?datasetVersionId=${dataset.latest_version_id ?? ""}`}
                      className="sk-btn sk-btn-muted px-3 py-1.5"
                    >
                      Preview
                    </Link>
                    <Link
                      href={`/generate-dataset?datasetId=${dataset.id}&datasetVersionId=${dataset.latest_version_id ?? ""}`}
                      className="sk-btn sk-btn-muted px-3 py-1.5"
                    >
                      Generate
                    </Link>
                    <button
                      type="button"
                      className="sk-btn sk-btn-danger px-3 py-1.5"
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
