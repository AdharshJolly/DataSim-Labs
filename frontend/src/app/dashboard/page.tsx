"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  me,
  listDatasets,
  listGenerationJobs,
  retryGenerationJob,
  deleteDataset,
  logout,
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
  ChevronDown,
  HelpCircle,
  Menu,
  Search,
  Keyboard,
} from "lucide-react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { TemplateGrid } from "@/components/studio/template-grid";
import { useErrorNotifier } from "@/lib/use-error-notifier";
import { KeyboardShortcutsModal } from "@/components/keyboard-shortcuts-modal";
import {
  StudioCommandPalette,
  StudioCommandGroup,
  StudioCommandItem,
} from "@/components/studio-command-palette";

interface CreateDatasetChooserProps {
  buttonLabel: string;
  onChooseTemplate: () => void;
  fullWidth?: boolean;
}

function CreateDatasetChooser({
  buttonLabel,
  onChooseTemplate,
  fullWidth = false,
}: CreateDatasetChooserProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const chooserRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (!chooserRef.current) return;
      if (!chooserRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const chooseBlank = () => {
    setIsOpen(false);
    router.push("/studio?new=true");
  };

  const chooseTemplate = () => {
    setIsOpen(false);
    onChooseTemplate();
  };

  return (
    <div
      ref={chooserRef}
      className={fullWidth ? "relative w-full" : "relative"}
    >
      <Button
        type="button"
        variant="cyber"
        className={fullWidth ? "min-h-12 w-full" : "min-h-12"}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <Plus className="mr-2 h-4 w-4" />
        {buttonLabel}
      </Button>

      {isOpen && (
        <Card className="absolute right-0 z-40 mt-2 w-72 border-border bg-background p-2 shadow-2xl">
          <button
            type="button"
            onClick={chooseBlank}
            className="flex w-full items-start gap-2 rounded-md px-3 py-2 text-left transition-colors hover:bg-white/5"
          >
            <Plus className="mt-0.5 h-4 w-4 text-primary" />
            <span>
              <span className="block text-sm font-medium text-foreground">
                Blank Dataset
              </span>
              <span className="block text-xs text-muted-foreground">
                Start from scratch in Studio
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={chooseTemplate}
            className="flex w-full items-start gap-2 rounded-md px-3 py-2 text-left transition-colors hover:bg-white/5"
          >
            <Database className="mt-0.5 h-4 w-4 text-primary" />
            <span>
              <span className="block text-sm font-medium text-foreground">
                Choose From Template
              </span>
              <span className="block text-xs text-muted-foreground">
                Pick a domain template first
              </span>
            </span>
          </button>
        </Card>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [jobs, setJobs] = useState<GenerationJobResponse[]>([]);
  const [showJobsPanel, setShowJobsPanel] = useState(false);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [keyboardHelpOpen, setKeyboardHelpOpen] = useState(false);
  const { notifyError } = useErrorNotifier(setError);

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
      notifyError("Dashboard Load Failed", err, "Failed to load dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  // Keyboard shortcuts handler
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isModifier = event.metaKey || event.ctrlKey;
      const isAltShortcut =
        event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
      const target = event.target as HTMLElement | null;
      const isTypingTarget =
        target != null &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable);
      const key = event.key.toLowerCase();

      // Escape key - close all overlays
      if (event.key === "Escape") {
        setCommandPaletteOpen(false);
        setKeyboardHelpOpen(false);
        setMobileMenuOpen(false);
        setShowTemplatePicker(false);
        setShowJobsPanel(false);
        return;
      }

      // Cmd/Ctrl+K - Open command palette
      if (isModifier && key === "k") {
        event.preventDefault();
        setCommandPaletteOpen(true);
        return;
      }

      // Alt+N - Create new dataset (Ctrl/Cmd+N is browser-reserved)
      if (isAltShortcut && key === "n" && !isTypingTarget) {
        event.preventDefault();
        router.push("/studio?new=true");
        return;
      }

      // Alt+T - Choose template (Ctrl/Cmd+T is browser-reserved)
      if (isAltShortcut && key === "t" && !isTypingTarget) {
        event.preventDefault();
        setShowTemplatePicker(true);
        return;
      }

      // Cmd/Ctrl+J - Toggle jobs panel
      if (isModifier && key === "j") {
        event.preventDefault();
        setShowJobsPanel((prev) => !prev);
        return;
      }

      // Cmd/Ctrl+/ - Show keyboard help
      if (isModifier && key === "/") {
        event.preventDefault();
        setKeyboardHelpOpen(true);
        return;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [router, datasets]);

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
      notifyError("Delete Dataset Failed", err, "Delete failed");
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
      notifyError("Retry Job Failed", err, "Retry failed");
    } finally {
      setRetryingJobId(null);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Ignore logout API failures; client navigation still resets session UX.
    }
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
        variant: "success",
      },
      generating: {
        icon: LoaderCircle,
        text: "Generating",
        variant: "cyber",
      },
      draft: {
        icon: Pencil,
        text: "Draft",
        variant: "warning",
      },
      archived: {
        icon: Archive,
        text: "Archived",
        variant: "secondary",
      },
    } as const;

    const current = statusMap[status];
    const shouldSpin = status === "generating";
    return (
      <Badge
        variant={
          current.variant as
            | "success"
            | "cyber"
            | "warning"
            | "secondary"
            | "default"
            | "destructive"
            | "outline"
        }
        className="gap-1.5 px-2 py-1 text-xs"
      >
        <current.icon
          className={shouldSpin ? "h-3 w-3 animate-spin" : "h-3 w-3"}
        />
        {current.text}
      </Badge>
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
            {/* Keyboard shortcut hint */}
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              className="hidden gap-2 rounded-lg border border-border/50 bg-white/5 px-3 py-2.5 text-sm text-muted-foreground transition-all hover:border-primary/50 hover:bg-primary/10 hover:text-foreground md:flex items-center"
              aria-label="Open command palette"
            >
              <Search className="h-4 w-4" />
              <span>Quick search</span>
              <kbd className="ml-auto rounded px-1.5 bg-white/10 font-mono text-xs">
                Ctrl+K
              </kbd>
            </button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-12 w-12 md:hidden"
              aria-label="Open dashboard menu"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <Button
              type="button"
              variant="outline"
              className="min-h-12"
              onClick={() => setShowJobsPanel((prev) => !prev)}
            >
              {showJobsPanel ? "Hide Jobs" : "My Jobs"}
              <Badge variant="outline" className="ml-2 px-2 py-0.5 text-xs">
                {jobs.length}
              </Badge>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="min-h-12"
              onClick={() => setKeyboardHelpOpen(true)}
              aria-label="Show keyboard shortcuts"
              title="Keyboard shortcuts (Ctrl+/)"
            >
              <Keyboard className="h-4 w-4" />
            </Button>
            <CreateDatasetChooser
              buttonLabel="Create Dataset"
              onChooseTemplate={() => setShowTemplatePicker(true)}
            />
            <Button
              type="button"
              variant="outline"
              className="group min-h-12 hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 transition-transform group-hover:scale-110" />
            </Button>
          </div>
        </div>

        {mobileMenuOpen && (
          <>
            <button
              type="button"
              className="fixed inset-0 z-40 bg-black/40 md:hidden"
              aria-label="Close mobile dashboard menu"
              onClick={() => setMobileMenuOpen(false)}
            />
            <Card className="fixed right-4 top-24 z-50 w-[min(320px,90vw)] border-border bg-background p-2 md:hidden">
              <button
                type="button"
                className="flex min-h-12 w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm text-foreground transition-colors hover:bg-white/5"
                onClick={() => {
                  setMobileMenuOpen(false);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                <Database className="h-4 w-4 text-primary" />
                Dataset List
              </button>
              <button
                type="button"
                className="flex min-h-12 w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm text-foreground transition-colors hover:bg-white/5"
                onClick={() => {
                  setMobileMenuOpen(false);
                  router.push("/studio?new=true");
                }}
              >
                <Plus className="h-4 w-4 text-primary" />
                Create New Dataset
              </button>
              <button
                type="button"
                className="flex min-h-12 w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm text-foreground transition-colors hover:bg-white/5"
                onClick={() => {
                  setMobileMenuOpen(false);
                  router.push("/terms");
                }}
              >
                <HelpCircle className="h-4 w-4 text-primary" />
                Help
              </button>
            </Card>
          </>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-5 w-5" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError("")}
                className="rounded-full p-1 transition-colors hover:bg-destructive/20"
              >
                <X className="h-4 w-4" />
              </button>
            </AlertDescription>
          </Alert>
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
            <div className="w-full max-w-sm">
              <CreateDatasetChooser
                buttonLabel="Create Your First Dataset"
                onChooseTemplate={() => setShowTemplatePicker(true)}
                fullWidth
              />
            </div>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {datasets.map((dataset) => (
              <Card
                key={dataset.id}
                className="group flex flex-col gap-4 rounded-2xl bg-gradient-to-br from-white/[0.05] to-transparent p-5 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/5"
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
                    No active export files found. Regenerate to download again.
                  </p>
                )}

                <div className="mt-auto flex flex-wrap gap-2 pt-2">
                  <Button
                    asChild
                    variant="cyber"
                    className="h-9 flex-1 text-xs px-3"
                  >
                    <Link href={`/studio?datasetId=${dataset.id}`}>
                      <Pencil className="mr-1.5 h-3 w-3" />
                      Open Studio
                    </Link>
                  </Button>
                  {dataset.latest_version_id && dataset.status !== "draft" && (
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      className="h-9 px-3 hover:border-secondary hover:text-secondary"
                    >
                      <Link href={`/download?datasetId=${dataset.id}`}>
                        <Download className="h-3 w-3" />
                      </Link>
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={deletingId === dataset.id}
                    className="h-9 px-3 hover:border-destructive hover:bg-destructive/20 hover:text-destructive"
                    onClick={() => void onDelete(dataset.id)}
                  >
                    {deletingId === dataset.id ? (
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
      {showTemplatePicker && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Choose a dataset template"
        >
          <Card className="max-h-[85vh] w-full max-w-5xl overflow-y-auto border-border bg-background p-6">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="font-display text-2xl font-bold text-foreground">
                  Choose a Template
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Select a schema and continue in Studio.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => setShowTemplatePicker(false)}
                aria-label="Close template picker"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <TemplateGrid
              showCreateLink={false}
              onSelectTemplate={async (template) => {
                setShowTemplatePicker(false);
                router.push(
                  `/studio?new=true&template=${encodeURIComponent(template.id)}`,
                );
              }}
            />
          </Card>
        </div>
      )}

      {datasets.length !== 0 && (
        <>
          {showJobsPanel && (
            <button
              type="button"
              aria-label="Close jobs panel"
              onClick={() => setShowJobsPanel(false)}
              className="fixed inset-0 z-[70] bg-black/20 backdrop-blur-[1px]"
            />
          )}

          <aside
            className={`fixed right-0 top-0 bottom-0 z-[80] w-full max-w-md transform border-l border-border bg-[#0b0f1a]/95 shadow-2xl transition-transform duration-300 ease-out will-change-transform ${
              showJobsPanel ? "translate-x-0" : "translate-x-full"
            }`}
            aria-hidden={!showJobsPanel}
          >
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-border px-5 py-4">
                <div>
                  <h2 className="font-display text-2xl font-bold">My Jobs</h2>
                  <p className="text-xs text-muted-foreground">
                    Latest {jobs.length}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => setShowJobsPanel(false)}
                  aria-label="Close jobs panel"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {jobs.length === 0 ? (
                  <Card className="p-5 text-sm text-muted-foreground">
                    No jobs yet. Start a generation run to see activity here.
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {jobs.slice(0, 12).map((job) => {
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
                            <Button
                              asChild
                              variant="outline"
                              size="sm"
                              className="h-8"
                            >
                              <Link
                                href={`/studio?datasetId=${job.dataset_id}`}
                              >
                                Open
                              </Link>
                            </Button>
                            {canRetry && (
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="h-8 hover:border-cyan-300 hover:text-cyan-300"
                                disabled={retryingJobId === job.job_id}
                                onClick={() => void onRetryJob(job.job_id)}
                              >
                                {retryingJobId === job.job_id ? (
                                  <LoaderCircle className="h-3 w-3 animate-spin" />
                                ) : (
                                  <RefreshCw className="h-3 w-3" />
                                )}
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </aside>
        </>
      )}

      {/* Command Palette */}
      <StudioCommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
      >
        <StudioCommandGroup heading="Navigation">
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              router.push("/dashboard");
            }}
          >
            <Search className="h-4 w-4 text-cyan-300" />
            Dataset List
          </StudioCommandItem>
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              router.push("/studio?new=true");
            }}
          >
            <Plus className="h-4 w-4 text-cyan-300" />
            Create New Dataset
          </StudioCommandItem>
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              setShowTemplatePicker(true);
            }}
          >
            <Database className="h-4 w-4 text-cyan-300" />
            Choose Template
          </StudioCommandItem>
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              router.push("/terms");
            }}
          >
            <HelpCircle className="h-4 w-4 text-cyan-300" />
            Help
          </StudioCommandItem>
        </StudioCommandGroup>

        <StudioCommandGroup heading="Actions">
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              setShowJobsPanel((prev) => !prev);
            }}
          >
            <LoaderCircle className="h-4 w-4 text-cyan-300" />
            Toggle Jobs Panel
          </StudioCommandItem>
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              setKeyboardHelpOpen(true);
            }}
          >
            <Keyboard className="h-4 w-4 text-cyan-300" />
            Keyboard Shortcuts
          </StudioCommandItem>
          <StudioCommandItem
            onSelect={() => {
              setCommandPaletteOpen(false);
              handleLogout();
            }}
          >
            <LogOut className="h-4 w-4 text-cyan-300" />
            Logout
          </StudioCommandItem>
        </StudioCommandGroup>

        {datasets.length > 0 && (
          <StudioCommandGroup heading="Datasets">
            {datasets.slice(0, 8).map((dataset) => (
              <StudioCommandItem
                key={dataset.id}
                onSelect={() => {
                  setCommandPaletteOpen(false);
                  router.push(`/studio?datasetId=${dataset.id}`);
                }}
              >
                <Database className="h-4 w-4 text-cyan-300" />
                {dataset.name}
              </StudioCommandItem>
            ))}
          </StudioCommandGroup>
        )}
      </StudioCommandPalette>

      {/* Keyboard Help Modal */}
      <KeyboardShortcutsModal
        open={keyboardHelpOpen}
        onClose={() => setKeyboardHelpOpen(false)}
        shortcuts={[
          { keys: "Cmd/Ctrl + K", description: "Open command palette" },
          { keys: "Alt + N", description: "Create new dataset" },
          { keys: "Alt + T", description: "Choose template" },
          { keys: "Cmd/Ctrl + J", description: "Toggle jobs panel" },
          { keys: "Cmd/Ctrl + /", description: "Show keyboard help" },
          { keys: "Esc", description: "Close dialogs and menus" },
          { keys: "Tab / Enter", description: "Navigate and confirm controls" },
        ]}
      />
    </AuthGuard>
  );
}
