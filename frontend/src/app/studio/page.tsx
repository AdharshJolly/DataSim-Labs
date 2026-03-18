"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Download,
  LoaderCircle,
  Plus,
  X,
} from "lucide-react";

import { AttrCard } from "@/components/studio/attr-card";
import { FORMAT_OPTIONS, STEP_LABELS } from "@/components/studio/constants";
import {
  formatBytes,
  newAttr,
  toApiAttr,
  uid,
  validateCategoricalWeights,
} from "@/components/studio/helpers";
import { QuickAdjustCard } from "@/components/studio/quick-adjust-card";
import type { AttrRow, OutputFormat, Step } from "@/components/studio/types";
import {
  type AttributeConfig,
  cancelGenerationJob,
  generateDatasetAsync,
  getGenerationJob,
  type GeneratedFileInfo,
  type GenerationJobStatus,
  createDataset,
  downloadDatasetFile,
  generateDataset,
  getDatasetVersions,
  listDatasetFiles,
  previewDataset,
  saveAttributes,
} from "@/lib/api-client";

import { AuthGuard } from "@/components/auth/auth-guard";

const ASYNC_POLL_INTERVAL_MS = 1500;
const ASYNC_POLL_MAX_ATTEMPTS = 1200;
const AUTO_ASYNC_ROW_THRESHOLD = 50000;
const AUTO_ASYNC_CELL_THRESHOLD = 1000000;

// ─── Main Component ───────────────────────────────────────────────────────────

function templateRows(kind: "hr" | "ecommerce" | "healthcare"): AttrRow[] {
  const makeRow = (overrides: Partial<AttrRow>): AttrRow => ({
    _id: uid(),
    name: "field",
    description: "",
    type: "integer",
    distribution: "uniform",
    allow_nulls: false,
    null_percentage: 10,
    min: "0",
    max: "100",
    categories: "",
    weights: "",
    start_date: "",
    end_date: "",
    precision: "2",
    max_length: "64",
    true_probability: "0.5",
    skew_direction: "right",
    skew_intensity: "2",
    ...overrides,
  });

  if (kind === "hr") {
    return [
      makeRow({
        name: "full_name",
        description: "Employee full name",
        type: "name",
      }),
      makeRow({
        name: "age",
        description: "Age in years",
        type: "integer",
        min: "18",
        max: "65",
      }),
      makeRow({
        name: "department",
        description: "Department assignment",
        type: "categorical",
        distribution: "weighted_categorical",
        categories: "Engineering, Sales, Marketing, HR, Finance",
        weights: "35, 20, 15, 10, 20",
      }),
      makeRow({
        name: "job_role",
        description: "Employee role",
        type: "categorical",
        distribution: "weighted_categorical",
        categories: "Intern, Analyst, Engineer, Manager, Director",
        weights: "10, 20, 40, 20, 10",
      }),
      makeRow({
        name: "salary",
        description: "Annual salary",
        type: "float",
        min: "0",
        max: "250000",
        precision: "2",
      }),
      makeRow({
        name: "email",
        description: "Work email",
        type: "email",
      }),
      makeRow({
        name: "company",
        description: "Employer company",
        type: "categorical",
        categories: "Acme Labs, Nova Health, Orbit Systems",
      }),
    ];
  }

  if (kind === "ecommerce") {
    return [
      makeRow({
        name: "customer_name",
        description: "Customer name",
        type: "name",
      }),
      makeRow({
        name: "customer_email",
        description: "Customer email",
        type: "email",
      }),
      makeRow({
        name: "country",
        description: "Shipping country",
        type: "categorical",
        distribution: "weighted_categorical",
        categories: "India, United States, Canada, Australia, United Kingdom",
        weights: "30, 25, 15, 15, 15",
      }),
      makeRow({
        name: "state",
        description: "Shipping state/province",
        type: "categorical",
        categories:
          "Maharashtra, California, Texas, Ontario, Victoria, England",
      }),
      makeRow({
        name: "postal_code",
        description: "Postal code",
        type: "text",
        max_length: "10",
      }),
      makeRow({
        name: "order_value",
        description: "Order value",
        type: "float",
        min: "10",
        max: "2500",
      }),
    ];
  }

  return [
    makeRow({
      name: "patient_name",
      description: "Patient full name",
      type: "name",
    }),
    makeRow({
      name: "gender",
      description: "Biological sex/gender",
      type: "categorical",
      categories: "male, female, non-binary",
    }),
    makeRow({
      name: "age",
      description: "Age in years",
      type: "integer",
      min: "0",
      max: "95",
    }),
    makeRow({
      name: "diagnosis_group",
      description: "Primary diagnosis category",
      type: "categorical",
      categories: "Cardiac, Respiratory, Endocrine, Neuro, Ortho",
    }),
    makeRow({
      name: "admission_date",
      description: "Date of admission",
      type: "date",
      start_date: "2020-01-01",
      end_date: "2026-12-31",
    }),
    makeRow({
      name: "length_of_stay",
      description: "Length of stay (days)",
      type: "integer",
      min: "1",
      max: "45",
    }),
  ];
}

export default function StudioPage() {
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Step 1
  const [dsName, setDsName] = useState("");
  const [dsDesc, setDsDesc] = useState("");
  const [datasetId, setDatasetId] = useState("");

  // Step 2
  const [attrs, setAttrs] = useState<AttrRow[]>([newAttr(0)]);
  const [versionId, setVersionId] = useState("");
  const [correlationRulesText, setCorrelationRulesText] = useState("[]");

  // Step 3
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Step 4
  const [rowCount, setRowCount] = useState(1000);
  const [formats, setFormats] = useState<OutputFormat[]>(["csv"]);
  const [seed, setSeed] = useState("");
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileInfo[]>([]);
  const [qualityReport, setQualityReport] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [generationSignature, setGenerationSignature] = useState("");
  const [generationRunId, setGenerationRunId] = useState("");
  const [runComparison, setRunComparison] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [qualityGuardrails, setQualityGuardrails] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [realismMetadata, setRealismMetadata] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState<GenerationJobStatus | "">("");
  const [jobStage, setJobStage] = useState("");
  const [jobProgress, setJobProgress] = useState(0);
  const [driftEnabled, setDriftEnabled] = useState(false);
  const [driftIntensity, setDriftIntensity] = useState(0.1);
  const [driftColumnsText, setDriftColumnsText] = useState("");

  const estimatedCells = rowCount * Math.max(1, attrs.length);
  const useAsyncGeneration =
    rowCount >= AUTO_ASYNC_ROW_THRESHOLD ||
    estimatedCells >= AUTO_ASYNC_CELL_THRESHOLD;

  // Load existing dataset from query string
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const queryDatasetId = params.get("datasetId");
    const storedDatasetId = localStorage.getItem("datasim:dataset_id");
    const id = queryDatasetId || storedDatasetId;
    if (!id) return;

    setDatasetId(id);
    Promise.all([getDatasetVersions(id), listDatasetFiles(id)])
      .then(([resp, filesResponse]) => {
        const existingFiles = filesResponse.files ?? [];
        if (existingFiles.length > 0) {
          setGeneratedFiles(existingFiles);
        }

        if (resp.versions.length === 0) {
          setStep(existingFiles.length > 0 ? 4 : 2);
          return;
        }

        const latest = resp.versions[0];
        const cfgAttrs =
          (latest.config_json.attributes as AttributeConfig[] | undefined) ??
          [];
        if (cfgAttrs.length > 0) {
          setAttrs(
            cfgAttrs.map((a) => ({
              _id: uid(),
              name: a.name,
              description: a.description ?? "",
              type: a.type,
              distribution: a.distribution,
              allow_nulls: a.null_percentage > 0,
              null_percentage: a.null_percentage > 0 ? a.null_percentage : 10,
              min:
                a.constraints.min !== undefined
                  ? String(a.constraints.min)
                  : "0",
              max:
                a.constraints.max !== undefined
                  ? String(a.constraints.max)
                  : "100",
              categories: Array.isArray(a.constraints.categories)
                ? (a.constraints.categories as string[]).join(", ")
                : "",
              weights: Array.isArray(a.constraints.weights)
                ? (a.constraints.weights as number[]).join(", ")
                : "",
              start_date:
                typeof a.constraints.start_date === "string"
                  ? a.constraints.start_date
                  : "",
              end_date:
                typeof a.constraints.end_date === "string"
                  ? a.constraints.end_date
                  : "",
              precision:
                a.constraints.precision !== undefined
                  ? String(a.constraints.precision)
                  : "2",
              max_length:
                a.constraints.max_length !== undefined
                  ? String(a.constraints.max_length)
                  : "64",
              true_probability:
                a.constraints.true_probability !== undefined
                  ? String(a.constraints.true_probability)
                  : "0.5",
              skew_direction:
                a.constraints.skew_direction === "left" ? "left" : "right",
              skew_intensity:
                a.constraints.skew_intensity !== undefined
                  ? String(a.constraints.skew_intensity)
                  : "2",
            })),
          );
          setVersionId(latest.id);
          if (typeof latest.seed === "number") {
            setSeed(String(latest.seed));
          }
        }
        const realism = latest.config_json.realism as
          | { metadata?: Record<string, unknown> }
          | undefined;
        const correlations = latest.config_json.correlations;
        if (Array.isArray(correlations)) {
          setCorrelationRulesText(JSON.stringify(correlations, null, 2));
        }
        if (realism?.metadata) {
          setRealismMetadata(realism.metadata);
        }

        setStep(existingFiles.length > 0 ? 4 : 2);
      })
      .catch(() => setStep(2));
  }, []);

  const applyTemplate = (kind: "hr" | "ecommerce" | "healthcare") => {
    const templated = templateRows(kind);
    setAttrs(templated);
    setError("");
  };

  const parseCorrelationRules = () => {
    if (!correlationRulesText.trim()) {
      return [] as Array<{ source: string; target: string; strength: number }>;
    }
    const parsed = JSON.parse(correlationRulesText) as unknown;
    if (!Array.isArray(parsed)) {
      throw new Error("Correlation rules must be a JSON array.");
    }
    return parsed
      .filter(
        (item): item is Record<string, unknown> =>
          !!item && typeof item === "object",
      )
      .map((item) => ({
        source: String(item.source ?? "").trim(),
        target: String(item.target ?? "").trim(),
        strength: Number(item.strength ?? 0),
      }))
      .filter(
        (item) => item.source && item.target && !Number.isNaN(item.strength),
      );
  };

  // ── Step 1: Create Dataset ───────────────────────────────────
  const handleCreate = async () => {
    if (!dsName.trim()) {
      setError("Please enter a dataset name.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await createDataset({
        name: dsName.trim(),
        description: dsDesc.trim() || undefined,
      });
      setDatasetId(res.dataset_id);
      localStorage.setItem("datasim:dataset_id", res.dataset_id);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create dataset");
    } finally {
      setBusy(false);
    }
  };

  // ── Step 2: Save Attributes ──────────────────────────────────
  const handleSaveAndPreview = async () => {
    if (!datasetId) {
      setError("No dataset found. Please start from step 1.");
      return;
    }
    if (attrs.length === 0) {
      setError("Add at least one attribute.");
      return;
    }
    if (attrs.some((a) => !a.name.trim())) {
      setError("Every attribute must have a name.");
      return;
    }
    setBusy(true);
    setError("");
    // Client-side weight validation
    const weightError = attrs.map(validateCategoricalWeights).find(Boolean);
    if (weightError) {
      setBusy(false);
      setError(weightError);
      return;
    }
    try {
      const correlations = parseCorrelationRules();
      const res = await saveAttributes({
        dataset_id: datasetId,
        attributes: attrs.map(toApiAttr),
        seed: seed.trim() ? Number(seed) : undefined,
        correlations,
      });
      setVersionId(res.version_id);
      localStorage.setItem("datasim:dataset_version_id", res.version_id);
      setStep(3);
      await loadPreview(res.version_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save attributes");
    } finally {
      setBusy(false);
    }
  };

  // ── Step 3: Preview ──────────────────────────────────────────
  const loadPreview = async (vid?: string) => {
    const id = vid ?? versionId;
    if (!id) {
      setError("No version available.");
      return;
    }
    setIsRefreshing(true);
    setError("");
    try {
      const res = await previewDataset(
        id,
        seed.trim() ? Number(seed) : undefined,
      );
      setPreviewRows(res.data);
      setPreviewCols(res.data.length > 0 ? Object.keys(res.data[0]) : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRegenerate = async () => {
    if (!versionId) {
      setError("No saved version to preview.");
      return;
    }
    await loadPreview(versionId);
  };

  // ── Step 4: Generate ─────────────────────────────────────────
  const handleGenerate = async () => {
    if (!datasetId) {
      setError("No dataset selected.");
      return;
    }
    if (formats.length === 0) {
      setError("Select at least one output format.");
      return;
    }
    setBusy(true);
    setError("");
    // Client-side weight validation
    const weightError = attrs.map(validateCategoricalWeights).find(Boolean);
    if (weightError) {
      setBusy(false);
      setError(weightError);
      return;
    }
    try {
      const payload = {
        dataset_id: datasetId,
        dataset_version_id: versionId || undefined,
        row_count: rowCount,
        formats,
        seed: seed.trim() ? Number(seed) : undefined,
        drift_profile: {
          enabled: driftEnabled,
          intensity: driftIntensity,
          target_columns: driftColumnsText
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
        },
      };

      if (!useAsyncGeneration) {
        const res = await generateDataset(payload);
        setGeneratedFiles(res.files);
        setQualityReport(
          (res.quality_report as Record<string, unknown>) ?? null,
        );
        setQualityGuardrails(
          (res.quality_guardrails as Record<string, unknown>) ?? null,
        );
        setGenerationSignature(res.generation_signature ?? "");
        setGenerationRunId(res.generation_run_id ?? "");
        setRunComparison((res.comparison as Record<string, unknown>) ?? null);
        return;
      }

      const queued = await generateDatasetAsync(payload);
      setJobId(queued.job_id);
      setJobStatus(queued.status);
      setJobStage("queued");
      setJobProgress(0);

      const wait = (ms: number) =>
        new Promise((resolve) => {
          setTimeout(resolve, ms);
        });

      for (let attempt = 0; attempt < ASYNC_POLL_MAX_ATTEMPTS; attempt += 1) {
        const job = await getGenerationJob(queued.job_id);
        setJobStatus(job.status);
        setJobStage(job.stage);
        setJobProgress(job.progress_percentage);

        if (job.status === "completed") {
          const result = job.result;
          if (!result) {
            throw new Error(
              "Generation completed but no result payload returned.",
            );
          }
          setGeneratedFiles(result.files);
          setQualityReport(
            (result.quality_report as Record<string, unknown>) ?? null,
          );
          setQualityGuardrails(
            (result.quality_guardrails as Record<string, unknown>) ?? null,
          );
          setGenerationSignature(result.generation_signature ?? "");
          setGenerationRunId(result.generation_run_id ?? "");
          setRunComparison(
            (result.comparison as Record<string, unknown>) ?? null,
          );
          break;
        }

        if (job.status === "failed") {
          throw new Error(job.error || "Async generation job failed.");
        }

        if (job.status === "cancelled") {
          throw new Error("Async generation job was cancelled.");
        }

        await wait(ASYNC_POLL_INTERVAL_MS);

        if (attempt === ASYNC_POLL_MAX_ATTEMPTS - 1) {
          throw new Error("Timed out waiting for async generation job.");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleCancelJob = async () => {
    if (!jobId) {
      return;
    }
    try {
      const result = await cancelGenerationJob(jobId);
      setJobStatus(result.status);
      setJobStage("cancel_requested");
      if (result.status === "cancelled") {
        setJobProgress(100);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to cancel job");
    }
  };

  const handleDownload = async (format: string) => {
    try {
      const { blob, fileName } = await downloadDatasetFile(datasetId, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  };

  // ── Attribute helpers ────────────────────────────────────────
  const updateAttr = <K extends keyof AttrRow>(
    i: number,
    key: K,
    value: AttrRow[K],
  ) => {
    setAttrs((prev) =>
      prev.map((a, idx) => {
        if (idx !== i) return a;
        const next = { ...a, [key]: value };
        if (key === "type") {
          const nextType = value as AttrRow["type"];
          if (
            nextType !== "categorical" &&
            next.distribution === "weighted_categorical"
          ) {
            next.distribution = "uniform";
          }
          if (
            nextType === "boolean" ||
            nextType === "text" ||
            nextType === "email" ||
            nextType === "name" ||
            nextType === "address" ||
            nextType === "date"
          ) {
            next.distribution = "uniform";
          }
        }
        return next;
      }),
    );
  };

  const addAttr = () => setAttrs((prev) => [...prev, newAttr(prev.length)]);
  const removeAttr = (i: number) =>
    setAttrs((prev) => prev.filter((_, idx) => idx !== i));
  const toggleFormat = (f: OutputFormat) =>
    setFormats((prev) =>
      prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f],
    );

  // ─────────────────────────────────────────────────────────────

  return (
    <AuthGuard>
      <div className="flex min-h-[calc(100vh-10rem)] flex-col gap-0 md:flex-row md:gap-8">
        {/* ── Sidebar ── */}
        <aside className="hidden w-56 flex-shrink-0 md:block md:sticky md:top-24 h-fit max-h-[calc(100vh-8rem)] overflow-y-auto pr-4 pb-8">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
            Steps
          </p>
          <nav className="space-y-1">
            {STEP_LABELS.map(([num, label], i) => {
              const s = (i + 1) as Step;
              const done = step > s;
              const active = step === s;
              const inactive = s > step;
              return (
                <button
                  key={s}
                  type="button"
                  disabled={inactive}
                  onClick={() => {
                    if (done) setStep(s);
                  }}
                  className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                    active
                      ? "bg-primary/10 text-primary"
                      : done
                        ? "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                        : "cursor-not-allowed text-muted-foreground/50"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      active
                        ? "bg-primary text-primary-foreground"
                        : done
                          ? "bg-green-500/20 text-green-400 group-hover:bg-green-500/30"
                          : "bg-border text-muted-foreground"
                    }`}
                  >
                    {done ? <Check className="h-4 w-4" /> : num}
                  </span>
                  <span>{label}</span>
                </button>
              );
            })}
          </nav>

          {/* Dataset info */}
          {(dsName || datasetId) && (
            <div className="mt-8">
              <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                Dataset
              </p>
              <div className="rounded-lg border border-border bg-white/5 p-3">
                <p className="truncate font-semibold text-foreground">
                  {dsName || `ID: ${datasetId.substring(0, 8)}...`}
                </p>
                <p className="text-xs text-muted-foreground">
                  {attrs.length} {attrs.length === 1 ? "field" : "fields"}
                </p>
              </div>
            </div>
          )}
        </aside>

        {/* ── Main Content ── */}
        <div className="min-w-0 flex-1 pb-24">
          {/* Mobile step bar */}
          <div className="mb-6 md:hidden">
            <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
              Step {step} of {STEP_LABELS.length}
            </p>
            <div className="flex h-1.5 w-full items-center gap-1.5 rounded-full bg-border">
              {STEP_LABELS.map((_, i) => {
                const s = (i + 1) as Step;
                return (
                  <div
                    key={s}
                    className={`h-full flex-1 rounded-full ${
                      step >= s ? "bg-primary" : ""
                    }`}
                  />
                );
              })}
            </div>
          </div>

          {/* Error banner */}
          {error && (
            <div className="mb-6 flex items-start justify-between gap-4 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={() => setError("")}
                className="rounded-full p-1 transition-colors hover:bg-destructive/20"
                aria-label="Dismiss error"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* ════════════════ STEP 1 ════════════════ */}
          {step === 1 && (
            <div>
              <header className="mb-8">
                <h1 className="font-display text-4xl font-bold">
                  Start a New Dataset
                </h1>
                <p className="mt-2 text-muted-foreground">
                  Give your synthetic dataset a name and describe what it
                  represents. You&apos;ll define the fields next.
                </p>
              </header>

              <div className="max-w-lg space-y-6">
                <div className="space-y-2">
                  <label
                    htmlFor="ds-name"
                    className="text-sm font-medium text-muted-foreground"
                  >
                    Dataset Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="ds-name"
                    className="w-full"
                    placeholder="e.g. Project Chimera"
                    value={dsName}
                    onChange={(e) => setDsName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && void handleCreate()}
                    autoFocus
                  />
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor="ds-desc"
                    className="text-sm font-medium text-muted-foreground"
                  >
                    Description (optional)
                  </label>
                  <textarea
                    id="ds-desc"
                    className="h-24 w-full resize-none"
                    placeholder="What is this dataset for? Who will use it? What does it represent?"
                    value={dsDesc}
                    onChange={(e) => setDsDesc(e.target.value)}
                  />
                </div>
              </div>

              <div className="mt-8 flex items-center gap-3">
                <button
                  type="button"
                  disabled={busy || !dsName.trim()}
                  onClick={() => void handleCreate()}
                  className="btn-primary"
                >
                  {busy ? (
                    <span className="flex items-center justify-center gap-2">
                      <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                      Creating…
                    </span>
                  ) : (
                    "Create & Define Fields →"
                  )}
                </button>
                <Link
                  href="/dashboard"
                  className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:bg-white/5"
                >
                  Cancel
                </Link>
              </div>
            </div>
          )}

          {/* ════════════════ STEP 2 ════════════════ */}
          {step === 2 && (
            <div>
              <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h1 className="font-display text-4xl font-bold">
                    Define Your Fields
                  </h1>
                  <p className="mt-2 text-muted-foreground">
                    Each field becomes a column. Describe what it represents to
                    guide generation — the more detail, the better.
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy || attrs.length === 0}
                  onClick={() => void handleSaveAndPreview()}
                  className="btn-primary whitespace-nowrap"
                >
                  {busy ? (
                    <span className="flex items-center justify-center gap-2">
                      <LoaderCircle className="h-4 w-4 animate-spin" /> Saving…
                    </span>
                  ) : (
                    "Save & Preview →"
                  )}
                </button>
              </header>

              <div className="mb-8 rounded-lg border border-border bg-white/5 p-4">
                <p className="text-sm font-semibold text-foreground">
                  Start from a template
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Load a domain starter schema and customize from there.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => applyTemplate("hr")}
                    className="btn-secondary !h-9 !px-3 !text-xs"
                  >
                    HR Template
                  </button>
                  <button
                    type="button"
                    onClick={() => applyTemplate("ecommerce")}
                    className="btn-secondary !h-9 !px-3 !text-xs"
                  >
                    Ecommerce Template
                  </button>
                  <button
                    type="button"
                    onClick={() => applyTemplate("healthcare")}
                    className="btn-secondary !h-9 !px-3 !text-xs"
                  >
                    Healthcare Template
                  </button>
                </div>
              </div>

              <div className="mb-8 rounded-lg border border-border bg-white/5 p-4">
                <p className="text-sm font-semibold text-foreground">
                  Correlation Builder (optional)
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Define correlation rules as JSON array, for example:
                  <span className="ml-1 rounded bg-background/60 px-1 py-0.5 font-mono text-[11px]">
                    {'[{"source":"age","target":"income","strength":0.6}]'}
                  </span>
                </p>
                <textarea
                  className="mt-3 h-28 w-full"
                  value={correlationRulesText}
                  onChange={(e) => setCorrelationRulesText(e.target.value)}
                />
              </div>

              {/* Attribute list */}
              <div className="space-y-4">
                {attrs.map((attr, i) => (
                  <AttrCard
                    key={attr._id}
                    attr={attr}
                    index={i}
                    total={attrs.length}
                    onUpdate={updateAttr}
                    onRemove={removeAttr}
                  />
                ))}
              </div>

              {/* Add attribute button */}
              <button
                type="button"
                onClick={addAttr}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border py-4 text-sm font-semibold text-muted-foreground transition-all hover:border-primary/80 hover:bg-primary/10 hover:text-primary"
              >
                <Plus className="h-4 w-4" />
                Add Field
              </button>

              <div className="mt-8 flex items-center gap-3">
                <button
                  type="button"
                  disabled={busy || attrs.length === 0}
                  onClick={() => void handleSaveAndPreview()}
                  className="btn-primary"
                >
                  {busy ? "Saving…" : "Save & Preview →"}
                </button>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:bg-white/5"
                >
                  ← Back
                </button>
              </div>
            </div>
          )}

          {/* ════════════════ STEP 3 ════════════════ */}
          {step === 3 && (
            <div>
              <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h1 className="font-display text-4xl font-bold">
                    Preview & Refine
                  </h1>
                  <p className="mt-2 text-muted-foreground">
                    Review 10 sample rows. Tweak the field settings below and
                    regenerate until the data looks right.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:bg-white/5"
                  >
                    ← Edit Fields
                  </button>
                  <button
                    type="button"
                    disabled={isRefreshing}
                    onClick={() => void handleRegenerate()}
                    className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:bg-white/5"
                  >
                    {isRefreshing ? (
                      <span className="flex items-center gap-2">
                        <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                        Regenerating…
                      </span>
                    ) : (
                      "↺ Regenerate"
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(4)}
                    className="btn-primary"
                  >
                    Looks Good →
                  </button>
                </div>
              </header>

              {realismMetadata && (
                <div className="mb-6 rounded-lg border border-border bg-white/5 p-4">
                  <p className="text-sm font-semibold text-foreground">
                    Realism Planner Metadata
                  </p>
                  <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <span className="text-foreground">Source:</span>{" "}
                      {String(realismMetadata.source ?? "unknown")}
                    </div>
                    <div>
                      <span className="text-foreground">Planner:</span>{" "}
                      {String(realismMetadata.planner_version ?? "n/a")}
                    </div>
                    <div>
                      <span className="text-foreground">Validated Rules:</span>{" "}
                      {String(realismMetadata.validated_rule_count ?? 0)}
                    </div>
                    <div>
                      <span className="text-foreground">Conflicts:</span>{" "}
                      {Array.isArray(realismMetadata.conflicts)
                        ? realismMetadata.conflicts.length
                        : 0}
                    </div>
                  </div>

                  {Array.isArray(realismMetadata.conflicts) &&
                    realismMetadata.conflicts.length > 0 && (
                      <div className="mt-3 rounded border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
                        <p className="font-medium text-amber-100">
                          Detected rule conflicts
                        </p>
                        <ul className="mt-1 space-y-1">
                          {realismMetadata.conflicts
                            .slice(0, 3)
                            .map((item, idx) => {
                              const conflict = item as Record<string, unknown>;
                              return (
                                <li key={idx}>
                                  {String(conflict.type ?? "conflict")}:{" "}
                                  {String(
                                    conflict.details ?? "details unavailable",
                                  )}
                                </li>
                              );
                            })}
                        </ul>
                      </div>
                    )}

                  {Array.isArray(realismMetadata.rule_explanations) &&
                    realismMetadata.rule_explanations.length > 0 && (
                      <div className="mt-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground">
                          Rule explainability
                        </p>
                        <p className="mt-1">
                          {realismMetadata.rule_explanations.length} rule
                          explanations available in version metadata.
                        </p>
                      </div>
                    )}
                </div>
              )}

              {/* Preview table */}
              {isRefreshing ? (
                <div className="flex h-60 flex-col items-center justify-center gap-3 rounded-lg border border-border bg-background/70">
                  <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">
                    Generating sample…
                  </span>
                </div>
              ) : previewRows.length > 0 ? (
                <div className="overflow-x-auto rounded-lg border border-border">
                  <table className="min-w-full text-sm">
                    <thead className="border-b border-border/50 bg-white/5">
                      <tr>
                        {previewCols.map((col) => (
                          <th
                            key={col}
                            className="px-4 py-3 text-left font-medium text-muted-foreground"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {previewRows.map((row, ri) => (
                        <tr
                          key={ri}
                          className="transition-colors hover:bg-white/5"
                        >
                          {previewCols.map((col) => (
                            <td
                              key={col}
                              className="whitespace-nowrap px-4 py-3 text-foreground"
                            >
                              {row[col] == null ? (
                                <span className="italic text-muted-foreground/60">
                                  null
                                </span>
                              ) : (
                                String(row[col])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="flex h-60 items-center justify-center rounded-lg border-2 border-dashed border-border/50 text-sm text-muted-foreground">
                  No preview data yet — click Regenerate.
                </div>
              )}

              {/* Quick‑adjust cards */}
              <div className="mt-12">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-display text-2xl font-bold">
                    Quick Adjustments
                  </h2>
                  <button
                    type="button"
                    disabled={isRefreshing}
                    onClick={() => void handleRegenerate()}
                    className="btn-secondary !h-9 !px-3 !text-xs"
                  >
                    {isRefreshing ? "…" : "↺ Apply & Regenerate"}
                  </button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {attrs.map((attr, i) => (
                    <QuickAdjustCard
                      key={attr._id}
                      attr={attr}
                      index={i}
                      onUpdate={updateAttr}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ════════════════ STEP 4 ════════════════ */}
          {step === 4 && (
            <div>
              {generatedFiles.length === 0 ? (
                <>
                  <header className="mb-8">
                    <h1 className="font-display text-4xl font-bold">
                      Generate Your Dataset
                    </h1>
                    <p className="mt-2 text-muted-foreground">
                      Choose how many rows you need and which formats to export.
                    </p>
                  </header>

                  <div className="max-w-xl space-y-8">
                    {/* Row count */}
                    <div className="space-y-2">
                      <label
                        htmlFor="row-count"
                        className="text-sm font-medium text-muted-foreground"
                      >
                        Number of Rows
                      </label>
                      <div className="flex items-center gap-4">
                        <input
                          id="row-count"
                          type="range"
                          min={100}
                          max={100000}
                          step={100}
                          value={rowCount}
                          onChange={(e) => setRowCount(Number(e.target.value))}
                          className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                        />
                        <input
                          type="number"
                          min={1}
                          max={10000000}
                          className="w-32 text-center font-semibold"
                          value={rowCount}
                          onChange={(e) =>
                            setRowCount(
                              Math.max(1, Number(e.target.value) || 1),
                            )
                          }
                        />
                      </div>
                    </div>

                    {/* Format selection */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-muted-foreground">
                        Output Format
                      </label>
                      <div className="mt-1 flex flex-wrap gap-3">
                        {FORMAT_OPTIONS.map(({ value, label, icon: Icon }) => (
                          <button
                            key={value}
                            type="button"
                            onClick={() => toggleFormat(value)}
                            className={`flex h-24 w-24 flex-col items-center justify-center gap-1.5 rounded-lg border-2 text-sm font-semibold transition-all duration-150 ${
                              formats.includes(value)
                                ? "border-primary bg-primary/10 text-primary shadow-lg shadow-primary/10"
                                : "border-border bg-white/5 text-muted-foreground hover:border-primary/50 hover:bg-primary/5"
                            }`}
                          >
                            <Icon className="h-6 w-6" />
                            <span>{label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label
                        htmlFor="generation-seed"
                        className="text-sm font-medium text-muted-foreground"
                      >
                        Reproducibility Seed (optional)
                      </label>
                      <input
                        id="generation-seed"
                        type="number"
                        min={0}
                        className="w-48"
                        value={seed}
                        placeholder="e.g. 42"
                        onChange={(e) => setSeed(e.target.value)}
                      />
                      <p className="pt-1 text-xs text-muted-foreground/70">
                        Use the same seed to regenerate identical datasets.
                      </p>
                    </div>

                    <div className="space-y-3 rounded-lg border border-border bg-white/5 p-4">
                      <p className="text-sm font-medium text-foreground">
                        Generation mode:{" "}
                        {useAsyncGeneration ? "Background job" : "Immediate"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Auto-selected by thresholds (
                        {AUTO_ASYNC_ROW_THRESHOLD.toLocaleString()} rows or{" "}
                        {AUTO_ASYNC_CELL_THRESHOLD.toLocaleString()} estimated
                        cells).
                      </p>

                      {jobId && (
                        <div className="space-y-2 text-xs text-muted-foreground">
                          <div>
                            <span className="text-foreground">Job ID:</span>{" "}
                            {jobId}
                          </div>
                          <div>
                            <span className="text-foreground">Status:</span>{" "}
                            {jobStatus || "queued"}
                          </div>
                          <div>
                            <span className="text-foreground">Stage:</span>{" "}
                            {jobStage || "queued"}
                          </div>
                          <div>
                            <span className="text-foreground">Progress:</span>{" "}
                            {jobProgress}%
                          </div>
                          <div className="h-2 w-full overflow-hidden rounded bg-border">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{
                                width: `${Math.max(0, Math.min(100, jobProgress))}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="space-y-3 rounded-lg border border-border bg-white/5 p-4">
                      <label className="inline-flex items-center gap-2 text-sm font-medium text-foreground">
                        <input
                          type="checkbox"
                          className="h-4 w-4"
                          checked={driftEnabled}
                          onChange={(e) => setDriftEnabled(e.target.checked)}
                        />
                        Drift simulator
                      </label>
                      {driftEnabled && (
                        <>
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">
                              Drift intensity ({driftIntensity.toFixed(2)})
                            </label>
                            <input
                              type="range"
                              min={0}
                              max={1}
                              step={0.05}
                              value={driftIntensity}
                              onChange={(e) =>
                                setDriftIntensity(Number(e.target.value))
                              }
                              className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">
                              Target columns (comma separated)
                            </label>
                            <input
                              type="text"
                              value={driftColumnsText}
                              placeholder="age, income"
                              onChange={(e) =>
                                setDriftColumnsText(e.target.value)
                              }
                            />
                          </div>
                        </>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap items-center gap-3 pt-4">
                      <button
                        type="button"
                        onClick={() => setStep(3)}
                        className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:bg-white/5"
                      >
                        ← Back to Preview
                      </button>
                      <button
                        type="button"
                        disabled={busy || formats.length === 0}
                        onClick={() => void handleGenerate()}
                        className="btn-primary"
                      >
                        {busy ? (
                          <span className="flex items-center justify-center gap-2">
                            <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                            Generating…
                          </span>
                        ) : (
                          `Generate ${rowCount.toLocaleString()} Rows`
                        )}
                      </button>
                      {useAsyncGeneration && jobId && busy && (
                        <button
                          type="button"
                          onClick={() => void handleCancelJob()}
                          className="inline-flex h-11 items-center justify-center rounded-lg border border-amber-400/50 px-4 text-sm font-medium text-amber-200 transition-colors hover:bg-amber-500/10"
                        >
                          Cancel Job
                        </button>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                /* Success state */
                <div className="space-y-8">
                  <div className="flex items-center gap-4">
                    <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full bg-green-500/10 text-3xl text-green-400">
                      <CheckCircle2 className="h-10 w-10" />
                    </div>
                    <div>
                      <h2 className="font-display text-3xl font-bold">
                        Dataset Ready!
                      </h2>
                      <p className="text-muted-foreground">
                        {rowCount.toLocaleString()} rows · {attrs.length}{" "}
                        columns · {generatedFiles.length}{" "}
                        {generatedFiles.length === 1 ? "file" : "files"}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {generatedFiles.map((file) => (
                      <div
                        key={file.format}
                        className="flex items-center justify-between gap-3 rounded-lg border border-border bg-white/5 p-4"
                      >
                        <div>
                          <p className="font-bold uppercase">{file.format}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatBytes(file.size_bytes)}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void handleDownload(file.format)}
                          className="btn-secondary !h-9 !px-3 !text-xs"
                        >
                          <Download className="mr-1.5 h-3 w-3" />
                          Download
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="rounded-lg border border-border bg-white/5 p-4">
                    <h3 className="font-semibold text-foreground">
                      Generation Diagnostics
                    </h3>
                    <div className="mt-3 grid gap-3 text-xs text-muted-foreground sm:grid-cols-2">
                      <div>
                        <span className="text-foreground">Run ID:</span>{" "}
                        {generationRunId || "n/a"}
                      </div>
                      <div>
                        <span className="text-foreground">Signature:</span>{" "}
                        {generationSignature
                          ? `${generationSignature.slice(0, 16)}...`
                          : "n/a"}
                      </div>
                      <div>
                        <span className="text-foreground">
                          Rows affected by realism:
                        </span>{" "}
                        {String(
                          ((
                            qualityReport?.realism as
                              | Record<string, unknown>
                              | undefined
                          )?.total_rows_affected as number | undefined) ?? 0,
                        )}
                      </div>
                      <div>
                        <span className="text-foreground">Quality alerts:</span>{" "}
                        {Array.isArray(qualityReport?.alerts)
                          ? qualityReport.alerts.length
                          : 0}
                      </div>
                      <div>
                        <span className="text-foreground">Guardrails:</span>{" "}
                        {qualityGuardrails
                          ? String(
                              qualityGuardrails.passed ? "passed" : "failed",
                            )
                          : "n/a"}
                      </div>
                    </div>

                    {qualityGuardrails && (
                      <div className="mt-3 rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground">
                          Quality Guardrails
                        </p>
                        <p className="mt-1">
                          {String(qualityGuardrails.message ?? "")}
                        </p>
                        <p>
                          Alerts: {String(qualityGuardrails.actual_alerts ?? 0)}{" "}
                          / {String(qualityGuardrails.max_alerts ?? 0)}
                        </p>
                      </div>
                    )}

                    <div className="mt-3 rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
                      <p className="font-medium text-foreground">
                        Drift Simulation
                      </p>
                      <p className="mt-1">
                        {driftEnabled
                          ? `Enabled (intensity ${driftIntensity.toFixed(2)})`
                          : "Disabled"}
                      </p>
                    </div>

                    <div className="mt-3">
                      <p className="text-xs font-medium text-foreground">
                        Rule Impacts
                      </p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {Object.entries(
                          ((
                            qualityReport?.realism as
                              | Record<string, unknown>
                              | undefined
                          )?.rule_impacts as
                            | Record<string, number>
                            | undefined) ?? {},
                        ).map(([ruleType, count]) => (
                          <span
                            key={ruleType}
                            className="rounded border border-border bg-background/50 px-2 py-1 text-[11px] text-muted-foreground"
                          >
                            {ruleType}: {count}
                          </span>
                        ))}
                      </div>
                    </div>

                    {runComparison && (
                      <div className="mt-3 rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground">
                          Comparison With Previous Run
                        </p>
                        <p className="mt-1">
                          Delta realism-affected rows:{" "}
                          {String(runComparison.delta_rows_affected ?? 0)}
                        </p>
                        <p>
                          Previous run id:{" "}
                          {String(runComparison.previous_run_id ?? "n/a")}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setGeneratedFiles([]);
                        setQualityReport(null);
                        setQualityGuardrails(null);
                        setGenerationSignature("");
                        setGenerationRunId("");
                        setRunComparison(null);
                        setJobId("");
                        setJobStatus("");
                        setJobStage("");
                        setJobProgress(0);
                        setRowCount(1000);
                        setFormats(["csv"]);
                      }}
                      className="inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:border-border hover:bg-white/5"
                    >
                      Generate Again
                    </button>
                    <Link href="/dashboard" className="btn-primary">
                      Back to Dashboard
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
