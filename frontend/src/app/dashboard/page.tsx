"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  me,
  listDatasets,
  listGenerationJobs,
  retryGenerationJob,
  deleteDataset,
  logout,
  clearAuthToken,
  type DatasetSummary,
  type GenerationJobResponse,
} from "@/lib/api-client";
import {
  Plus,
  LogOut,
  LoaderCircle,
  X,
  Database,
  Pencil,
  Download,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Archive,
  RefreshCw,
  Clock3,
} from "lucide-react";

import { AuthGuard } from "@/components/auth/auth-guard";

export default function DashboardPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [jobs, setJobs] = useState<GenerationJobResponse[]>([]);
  const [showJobsPanel, setShowJobsPanel] = useState(false);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [profile, datasetResponse, jobsResponse] = await Promise.all([
        me(),
        listDatasets(),
        listGenerationJobs(12),
      ]);
      setEmail(profile.email);
      setDatasets(datasetResponse.datasets);
      setJobs(jobsResponse.jobs ?? []);
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
      setDatasets((prev) => prev.filter((d) => d.id !== datasetId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      void loadData();
    } finally {
      setDeletingId(null);
    }
  };

  const onRetryJob = async (jobId: string) => {
    setRetryingJobId(jobId);
    try {
      await retryGenerationJob(jobId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setRetryingJobId(null);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Ignore logout API failures and still clear local auth state.
    }
    clearAuthToken();
    window.location.href = "/login";
  };

  const datasetNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const dataset of datasets) {
      map.set(dataset.id, dataset.name);
    }
    return map;
  }, [datasets]);

  const StatusChip = ({ status }: { status: DatasetSummary["status"] }) => {
    const statusMap = {
      active: {
        icon: CheckCircle2,
        text: "Ready",
        className: "text-green-400 border-green-400/50 bg-green-400/10",
      },
      generating: {
        icon: LoaderCircle,
        text: "Generating",
        className: "text-cyan-300 border-cyan-300/50 bg-cyan-300/10",
      },
      draft: {
        icon: Pencil,
        text: "Draft",
        className: "text-amber-400 border-amber-400/50 bg-amber-400/10",
      },
      archived: {
        icon: Archive,
        text: "Archived",
        className: "text-gray-500 border-gray-500/50 bg-gray-500/10",
      },
    } as const;

    const current = statusMap[status];
    return (
      <span
        className={`inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-medium ${current.className}`}
      >
        <current.icon className="h-3 w-3" />
        {current.text}
      </span>
    );
  };

  return (
    <AuthGuard>
      <section className="space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl font-bold tracking-tight text-foreground">
              My Datasets
            </h1>
            {email && (
              <p className="mt-1 text-sm text-muted-foreground">
                Signed in as{" "}
                <span className="font-semibold text-primary">{email}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowJobsPanel((prev) => !prev)}
              className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-cyan-300/50 hover:bg-cyan-500/10 hover:text-cyan-200"
            >
              {showJobsPanel ? "Hide Jobs" : "My Jobs"}
              <span className="ml-2 rounded-full border border-border px-2 py-0.5 text-xs text-foreground">
                {jobs.length}
              </span>
            </button>
            <Link href="/studio" className="btn-cyber !h-11">
              <Plus className="mr-2 h-4 w-4" />
              New Dataset
            </Link>
            <button
              type="button"
              className="group flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 transition-transform group-hover:scale-110" />
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-start justify-between gap-4 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setError("")}
              className="rounded-full p-1 transition-colors hover:bg-destructive/20"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
            <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
            <p className="font-medium">Loading datasets...</p>
          </div>
        ) : datasets.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-6 rounded-2xl border-2 border-dashed border-border/50 py-24 text-center">
            <div className="relative flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-primary/10 shadow-inner shadow-primary/20">
              <Database className="h-10 w-10 text-primary" />
            </div>
            <div className="max-w-sm">
              <p className="font-display text-xl font-bold">No datasets yet</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Create your first synthetic dataset to get started.
              </p>
            </div>
            <Link href="/studio" className="btn-cyber !h-12">
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Dataset
            </Link>
          </div>
        ) : (
          <>
            {showJobsPanel && jobs.length > 0 && (
              <div className="rounded-2xl border border-border bg-white/5 p-5">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-display text-2xl font-bold">My Jobs</h2>
                  <span className="text-xs text-muted-foreground">
                    Latest {jobs.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {jobs.slice(0, 6).map((job) => {
                    const canRetry =
                      job.status === "failed" || job.status === "cancelled";
                    return (
                      <div
                        key={job.job_id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/70 bg-background/40 p-3 text-sm"
                      >
                        <div className="min-w-0">
                          <p className="truncate font-medium text-foreground">
                            {datasetNameById.get(job.dataset_id) ||
                              `Dataset ${job.dataset_id.slice(0, 8)}...`}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {job.status.toUpperCase()} ·{" "}
                            {job.progress_percentage}% ·{" "}
                            {new Date(job.created_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/studio?datasetId=${job.dataset_id}`}
                            className="inline-flex h-8 items-center justify-center rounded border border-border px-3 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                          >
                            Open
                          </Link>
                          {canRetry && (
                            <button
                              type="button"
                              disabled={retryingJobId === job.job_id}
                              onClick={() => void onRetryJob(job.job_id)}
                              className="inline-flex h-8 items-center justify-center rounded border border-border px-3 text-xs text-muted-foreground transition-colors hover:border-cyan-300 hover:text-cyan-300 disabled:opacity-60"
                            >
                              {retryingJobId === job.job_id ? (
                                <LoaderCircle className="h-3 w-3 animate-spin" />
                              ) : (
                                <RefreshCw className="h-3 w-3" />
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {showJobsPanel && jobs.length === 0 && (
              <div className="rounded-2xl border border-border bg-white/5 p-5 text-sm text-muted-foreground">
                No jobs yet. Start a generation run to see activity here.
              </div>
            )}

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {datasets.map((dataset) => (
                <div
                  key={dataset.id}
                  className="group flex flex-col gap-4 rounded-2xl border border-border bg-gradient-to-br from-white/[0.05] to-transparent p-5 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h2 className="truncate font-display text-xl font-bold">
                        {dataset.name}
                      </h2>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Created:{" "}
                        {new Date(dataset.created_at).toLocaleDateString(
                          undefined,
                          {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          },
                        )}
                      </p>
                    </div>
                    <StatusChip status={dataset.status} />
                  </div>

                  {dataset.description && (
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {dataset.description}
                    </p>
                  )}

                  {dataset.status === "draft" && dataset.latest_version_id && (
                    <p className="text-xs text-amber-300/90">
                      <Clock3 className="mr-1 inline h-3 w-3" />
                      No active export files found. Regenerate to download
                      again.
                    </p>
                  )}

                  <div className="mt-auto flex flex-wrap gap-2 pt-2">
                    <Link
                      href={`/studio?datasetId=${dataset.id}`}
                      className="btn-cyber !h-9 flex-1 !text-xs"
                    >
                      <Pencil className="mr-1.5 h-3 w-3" />
                      Open Studio
                    </Link>
                    {dataset.latest_version_id &&
                      dataset.status !== "draft" && (
                        <Link
                          href={`/download?datasetId=${dataset.id}`}
                          className="flex h-9 flex-shrink-0 items-center justify-center rounded-md border border-border px-3 text-xs font-medium text-muted-foreground transition-colors hover:border-secondary hover:text-secondary"
                        >
                          <Download className="h-3 w-3" />
                        </Link>
                      )}
                    <button
                      type="button"
                      disabled={deletingId === dataset.id}
                      className="flex h-9 flex-shrink-0 items-center justify-center rounded-md border border-border px-3 text-xs font-medium text-muted-foreground transition-colors hover:border-destructive hover:bg-destructive/20 hover:text-destructive disabled:pointer-events-none disabled:opacity-50"
                      onClick={() => void onDelete(dataset.id)}
                    >
                      {deletingId === dataset.id ? (
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-3 w-3" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </AuthGuard>
  );
}
