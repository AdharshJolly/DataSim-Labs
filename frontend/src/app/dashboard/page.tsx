"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  me,
  listDatasets,
  deleteDataset,
  logout,
  clearAuthToken,
  type DatasetSummary,
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
} from "lucide-react";

import { AuthGuard } from "@/components/auth/auth-guard";

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
      setDatasets(datasets.filter(d => d.id !== datasetId)); // Optimistic update
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      loadData(); // Re-fetch on error
    } finally {
      setDeletingId(null);
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
  
  const StatusChip = ({ status }: { status: DatasetSummary["status"] }) => {
    const statusMap = {
      active: { icon: CheckCircle2, text: "Ready", className: "text-green-400 border-green-400/50 bg-green-400/10" },
      draft: { icon: Pencil, text: "Draft", className: "text-amber-400 border-amber-400/50 bg-amber-400/10" },
      archived: { icon: Archive, text: "Archived", className: "text-gray-500 border-gray-500/50 bg-gray-500/10" },
    };
    const current = statusMap[status];
    return (
      <span className={`inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-medium ${current.className}`}>
        <current.icon className="h-3 w-3" />
        {current.text}
      </span>
    );
  };

  return (
    <AuthGuard>
      <section className="space-y-8">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl font-bold tracking-tight text-glow">
              My Datasets
            </h1>
            {email && (
              <p className="mt-1 text-sm text-muted-foreground">
                Signed in as <span className="font-semibold text-primary">{email}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
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

        {/* Error */}
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

        {/* Loading */}
        {isLoading ? (
          <div className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
            <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
            <p className="font-medium">Loading datasets...</p>
          </div>
        ) : datasets.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center gap-6 rounded-2xl border-2 border-dashed border-border/50 py-24 text-center">
             <div className="relative flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-primary/10">
                <Database className="h-10 w-10 text-primary" />
                <div className="absolute inset-0 animate-ping rounded-full border border-primary/30" />
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
          /* Dataset cards */
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="animate-subtle-float flex flex-col gap-4 rounded-2xl border border-border bg-white/5 p-5 backdrop-blur-sm transition-all duration-300 hover:border-primary/60 hover:shadow-2xl hover:shadow-primary/10">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h2 className="truncate font-display text-xl font-bold">
                      {dataset.name}
                    </h2>
                     <p className="mt-1 text-xs text-muted-foreground">
                      Created:{" "}
                      {new Date(dataset.created_at).toLocaleDateString(undefined, {
                        year: "numeric", month: "short", day: "numeric",
                      })}
                    </p>
                  </div>
                   <StatusChip status={dataset.status} />
                </div>

                 {dataset.description && (
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {dataset.description}
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
                  {dataset.latest_version_id && (
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
        )}
      </section>
    </AuthGuard>
  );
}
