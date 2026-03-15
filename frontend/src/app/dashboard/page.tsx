"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  type DatasetSummary,
  clearAuthToken,
  deleteDataset,
  listDatasets,
  logout,
  me,
} from "@/lib/api-client";

export default function DashboardPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [profile, datasetResponse] = await Promise.all([
        me(),
        listDatasets(),
      ]);
      setEmail(profile.email);
      setDatasets(datasetResponse.datasets);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const onDelete = async (datasetId: string) => {
    if (!confirm("Delete this dataset? This cannot be undone.")) return;
    setDeletingId(datasetId);
    try {
      await deleteDataset(datasetId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-[var(--font-title)] text-3xl font-black tracking-tight">
            My Datasets
          </h1>
          {email && (
            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
              Signed in as <span className="font-semibold">{email}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Link href="/studio" className="sk-btn sk-btn-primary gap-2">
            <span className="text-lg leading-none">+</span>
            New Dataset
          </Link>
          <button
            type="button"
            className="sk-btn sk-btn-muted"
            onClick={async () => {
              try {
                await logout();
              } catch {
                // Ignore logout API failures and still clear local auth state.
              }
              clearAuthToken();
              window.location.href = "/login";
            }}
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="sk-alert-error">
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={() => setError("")}
            className="text-red-400 hover:text-red-700"
          >
            ✕
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <span className="sk-spinner h-6 w-6 text-[hsl(var(--primary))]" />
        </div>
      ) : datasets.length === 0 ? (
        /* Empty state */
        <div className="flex flex-col items-center justify-center gap-5 rounded-2xl border-2 border-dashed border-[hsl(var(--border))] py-20">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[hsl(var(--muted))] text-3xl">
            ⊞
          </div>
          <div className="text-center">
            <p className="font-semibold">No datasets yet</p>
            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
              Create your first synthetic dataset to get started.
            </p>
          </div>
          <Link href="/studio" className="sk-btn sk-btn-primary">
            Create Your First Dataset
          </Link>
        </div>
      ) : (
        /* Dataset cards */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset) => (
            <div key={dataset.id} className="sk-panel flex flex-col gap-3 p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="truncate font-[var(--font-title)] text-lg font-bold">
                    {dataset.name}
                  </h2>
                  {dataset.description && (
                    <p className="mt-0.5 line-clamp-2 text-xs text-[hsl(var(--muted-foreground))]">
                      {dataset.description}
                    </p>
                  )}
                </div>
                {dataset.status === "active" ? (
                  <span className="sk-chip-success flex-shrink-0">Ready</span>
                ) : dataset.status === "archived" ? (
                  <span className="sk-chip-neutral flex-shrink-0">
                    Archived
                  </span>
                ) : (
                  <span className="sk-chip-neutral flex-shrink-0">Draft</span>
                )}
              </div>

              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Created{" "}
                {new Date(dataset.created_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </p>

              <div className="mt-auto flex flex-wrap gap-2 pt-1">
                <Link
                  href={`/studio?datasetId=${dataset.id}`}
                  className="sk-btn sk-btn-primary flex-1 justify-center py-2 text-xs"
                >
                  Open Studio
                </Link>
                {dataset.latest_version_id && (
                  <Link
                    href={`/download?datasetId=${dataset.id}`}
                    className="sk-btn sk-btn-muted py-2 text-xs"
                  >
                    Downloads
                  </Link>
                )}
                <button
                  type="button"
                  disabled={deletingId === dataset.id}
                  className="sk-btn sk-btn-danger py-2 text-xs"
                  onClick={() => void onDelete(dataset.id)}
                >
                  {deletingId === dataset.id ? "…" : "Delete"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
