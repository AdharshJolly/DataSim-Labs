"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  type AttributeConfig,
  type DataType,
  type DistributionType,
  type GeneratedFileInfo,
  createDataset,
  downloadDatasetFile,
  generateDataset,
  getDatasetVersions,
  previewDataset,
  saveAttributes,
} from "@/lib/api-client";

// ─── Types ───────────────────────────────────────────────────────────────────

type Step = 1 | 2 | 3 | 4;
type OutputFormat = "csv" | "json" | "excel";

interface AttrRow {
  _id: string;
  name: string;
  description: string;
  type: DataType;
  distribution: DistributionType;
  allow_nulls: boolean;
  null_percentage: number;
  // type-specific constraint fields
  min: string;
  max: string;
  categories: string;
  start_date: string;
  end_date: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STEP_LABELS: [string, string][] = [
  ["1", "Setup"],
  ["2", "Define Fields"],
  ["3", "Preview & Refine"],
  ["4", "Generate"],
];

const TYPE_OPTIONS: { value: DataType; label: string; icon: string }[] = [
  { value: "integer", label: "Integer", icon: "#" },
  { value: "float", label: "Decimal", icon: "~" },
  { value: "categorical", label: "Category", icon: "≡" },
  { value: "boolean", label: "True/False", icon: "◎" },
  { value: "date", label: "Date", icon: "▦" },
  { value: "text", label: "Text", icon: "T" },
  { value: "email", label: "Email", icon: "@" },
  { value: "name", label: "Full Name", icon: "✦" },
  { value: "address", label: "Address", icon: "⌂" },
];

const DIST_OPTIONS: { value: DistributionType; label: string }[] = [
  { value: "uniform", label: "Uniform" },
  { value: "normal", label: "Normal" },
  { value: "skewed", label: "Skewed" },
  { value: "weighted_categorical", label: "Weighted" },
];

const FORMAT_OPTIONS: { value: OutputFormat; label: string; ext: string }[] = [
  { value: "csv", label: "CSV", ext: ".csv" },
  { value: "json", label: "JSON", ext: ".json" },
  { value: "excel", label: "Excel", ext: ".xlsx" },
];

const NUMERIC_TYPES: DataType[] = ["integer", "float"];
const DIST_TYPES: DataType[] = ["integer", "float", "categorical"];

// ─── Helpers ──────────────────────────────────────────────────────────────────

let _uid = 0;
function uid() {
  return `attr-${Date.now()}-${++_uid}`;
}

function newAttr(index: number): AttrRow {
  return {
    _id: uid(),
    name: `field_${index + 1}`,
    description: "",
    type: "integer",
    distribution: "uniform",
    allow_nulls: false,
    null_percentage: 10,
    min: "0",
    max: "100",
    categories: "",
    start_date: "",
    end_date: "",
  };
}

function toApiAttr(attr: AttrRow): AttributeConfig {
  const constraints: Record<string, unknown> = {};
  if (NUMERIC_TYPES.includes(attr.type)) {
    if (attr.min !== "") constraints.min = Number(attr.min);
    if (attr.max !== "") constraints.max = Number(attr.max);
  } else if (attr.type === "categorical" && attr.categories.trim()) {
    constraints.categories = attr.categories
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  } else if (attr.type === "date") {
    if (attr.start_date) constraints.start_date = attr.start_date;
    if (attr.end_date) constraints.end_date = attr.end_date;
  }
  return {
    name: attr.name.trim() || `field_${Math.random().toString(36).slice(2, 6)}`,
    description: attr.description,
    type: attr.type,
    distribution: attr.distribution,
    null_percentage: attr.allow_nulls ? attr.null_percentage : 0,
    constraints,
  };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function typeLabel(t: DataType): string {
  return TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t;
}

// ─── Main Component ───────────────────────────────────────────────────────────

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

  // Step 3
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Step 4
  const [rowCount, setRowCount] = useState(1000);
  const [formats, setFormats] = useState<OutputFormat[]>(["csv"]);
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileInfo[]>([]);

  // Load existing dataset from query string
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("datasetId");
    if (!id) return;
    setDatasetId(id);
    getDatasetVersions(id)
      .then((resp) => {
        if (resp.versions.length === 0) {
          setStep(2);
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
              start_date:
                typeof a.constraints.start_date === "string"
                  ? a.constraints.start_date
                  : "",
              end_date:
                typeof a.constraints.end_date === "string"
                  ? a.constraints.end_date
                  : "",
            })),
          );
          setVersionId(latest.id);
        }
        setStep(2);
      })
      .catch(() => setStep(2));
  }, []);

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
    try {
      const res = await saveAttributes({
        dataset_id: datasetId,
        attributes: attrs.map(toApiAttr),
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
      const res = await previewDataset(id);
      setPreviewRows(res.data);
      setPreviewCols(res.data.length > 0 ? Object.keys(res.data[0]) : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRegenerate = async () => {
    if (!datasetId || attrs.length === 0) return;
    setIsRefreshing(true);
    setError("");
    try {
      const res = await saveAttributes({
        dataset_id: datasetId,
        attributes: attrs.map(toApiAttr),
      });
      setVersionId(res.version_id);
      localStorage.setItem("datasim:dataset_version_id", res.version_id);
      await loadPreview(res.version_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Regeneration failed");
      setIsRefreshing(false);
    }
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
    try {
      const res = await generateDataset({
        dataset_id: datasetId,
        dataset_version_id: versionId || undefined,
        row_count: rowCount,
        formats,
      });
      setGeneratedFiles(res.files);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
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
      prev.map((a, idx) => (idx === i ? { ...a, [key]: value } : a)),
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
    <div className="flex min-h-[calc(100vh-10rem)] flex-col gap-0 md:flex-row md:gap-8">
      {/* ── Sidebar ── */}
      <aside className="hidden w-52 flex-shrink-0 md:block">
        {/* Back link */}
        <Link
          href="/dashboard"
          className="mb-6 flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))] transition hover:text-[hsl(var(--foreground))]"
        >
          ← Dashboard
        </Link>

        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--muted-foreground))]">
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
                className={`studio-sidebar-item ${
                  active
                    ? "studio-sidebar-active"
                    : done
                      ? "studio-sidebar-done"
                      : "studio-sidebar-inactive"
                }`}
              >
                <span
                  className={`studio-step-num ${
                    active
                      ? "studio-step-num-active"
                      : done
                        ? "studio-step-num-done"
                        : "studio-step-num-inactive"
                  }`}
                >
                  {done ? "✓" : num}
                </span>
                {label}
              </button>
            );
          })}
        </nav>

        {/* Dataset info */}
        {dsName && (
          <div className="mt-6 rounded-xl border border-[hsl(var(--border))] bg-[rgba(240,228,210,0.4)] p-3">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--muted-foreground))]">
              Dataset
            </p>
            <p className="mt-0.5 truncate text-sm font-semibold">{dsName}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              {attrs.length} {attrs.length === 1 ? "attribute" : "attributes"}
            </p>
          </div>
        )}
      </aside>

      {/* ── Main Content ── */}
      <div className="min-w-0 flex-1">
        {/* Mobile step bar */}
        <div className="mobile-step-bar mb-5">
          {STEP_LABELS.map(([num], i) => {
            const s = (i + 1) as Step;
            const done = step > s;
            const active = step === s;
            return (
              <div key={s} className="flex items-center gap-1">
                <span
                  className={`mobile-step-dot text-xs ${
                    active
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                      : done
                        ? "bg-emerald-600 text-white"
                        : "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]"
                  }`}
                >
                  {done ? "✓" : num}
                </span>
                {i < STEP_LABELS.length - 1 && (
                  <div className="mobile-step-connector" />
                )}
              </div>
            );
          })}
        </div>

        {/* Mobile back link */}
        <Link
          href="/dashboard"
          className="mb-4 flex items-center gap-1 text-sm text-[hsl(var(--muted-foreground))] transition hover:text-[hsl(var(--foreground))] md:hidden"
        >
          ← Dashboard
        </Link>

        {/* Error banner */}
        {error && (
          <div className="sk-alert-error mb-5">
            <span className="flex-1">{error}</span>
            <button
              type="button"
              onClick={() => setError("")}
              className="flex-shrink-0 text-red-400 hover:text-red-700"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}

        {/* ════════════════ STEP 1 ════════════════ */}
        {step === 1 && (
          <div className="studio-card">
            <header className="mb-8">
              <h1 className="font-[var(--font-title)] text-3xl font-black tracking-tight">
                Start a New Dataset
              </h1>
              <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                Give your synthetic dataset a name and describe what it
                represents. You&apos;ll define the fields next.
              </p>
            </header>

            <div className="grid max-w-lg gap-5">
              <div className="studio-field">
                <label htmlFor="ds-name" className="studio-label">
                  Dataset Name{" "}
                  <span className="text-red-500" aria-hidden>
                    *
                  </span>
                </label>
                <input
                  id="ds-name"
                  className="sk-input"
                  placeholder="e.g. Patient Survey 2025"
                  value={dsName}
                  onChange={(e) => setDsName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && void handleCreate()}
                  autoFocus
                />
              </div>

              <div className="studio-field">
                <label htmlFor="ds-desc" className="studio-label">
                  Description{" "}
                  <span className="text-xs font-normal text-[hsl(var(--muted-foreground))]">
                    (optional)
                  </span>
                </label>
                <textarea
                  id="ds-desc"
                  className="sk-textarea h-24 resize-none"
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
                className="sk-btn sk-btn-primary px-8 py-3 text-base"
              >
                {busy ? (
                  <span className="flex items-center gap-2">
                    <span className="sk-spinner h-4 w-4" /> Creating…
                  </span>
                ) : (
                  "Create & Define Fields →"
                )}
              </button>
              <Link href="/dashboard" className="sk-btn sk-btn-muted">
                Cancel
              </Link>
            </div>
          </div>
        )}

        {/* ════════════════ STEP 2 ════════════════ */}
        {step === 2 && (
          <div className="studio-card">
            <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="font-[var(--font-title)] text-3xl font-black tracking-tight">
                  Define Your Fields
                </h1>
                <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                  Each field becomes a column. Describe what it represents to
                  guide generation — the more detail, the better.
                </p>
              </div>
              <button
                type="button"
                disabled={busy || attrs.length === 0}
                onClick={() => void handleSaveAndPreview()}
                className="sk-btn sk-btn-primary whitespace-nowrap"
              >
                {busy ? (
                  <span className="flex items-center gap-2">
                    <span className="sk-spinner h-4 w-4" /> Saving…
                  </span>
                ) : (
                  "Preview 10 Rows →"
                )}
              </button>
            </header>

            {/* Attribute list */}
            <div className="space-y-3">
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
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[hsl(var(--border))] py-4 text-sm font-semibold text-[hsl(var(--muted-foreground))] transition-all hover:border-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.04)] hover:text-[hsl(var(--primary))]"
            >
              <span className="text-xl leading-none">+</span>
              Add Field
            </button>

            <div className="mt-6 flex items-center gap-3">
              <button
                type="button"
                disabled={busy || attrs.length === 0}
                onClick={() => void handleSaveAndPreview()}
                className="sk-btn sk-btn-primary"
              >
                {busy ? "Saving…" : "Preview 10 Rows →"}
              </button>
              <button
                type="button"
                onClick={() => setStep(1)}
                className="sk-btn sk-btn-muted"
              >
                ← Back
              </button>
            </div>
          </div>
        )}

        {/* ════════════════ STEP 3 ════════════════ */}
        {step === 3 && (
          <div className="studio-card">
            <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="font-[var(--font-title)] text-3xl font-black tracking-tight">
                  Preview & Refine
                </h1>
                <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                  Review 10 sample rows. Tweak the field settings below and
                  regenerate until the data looks right.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="sk-btn sk-btn-muted"
                >
                  ← Edit Fields
                </button>
                <button
                  type="button"
                  disabled={isRefreshing}
                  onClick={() => void handleRegenerate()}
                  className="sk-btn sk-btn-muted"
                >
                  {isRefreshing ? (
                    <span className="flex items-center gap-2">
                      <span className="sk-spinner h-4 w-4" /> Regenerating…
                    </span>
                  ) : (
                    "↺ Regenerate"
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setStep(4)}
                  className="sk-btn sk-btn-primary"
                >
                  Looks Good →
                </button>
              </div>
            </header>

            {/* Preview table */}
            {isRefreshing ? (
              <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-2xl border border-[hsl(var(--border))] bg-[rgba(240,228,210,0.3)]">
                <span className="sk-spinner h-6 w-6 text-[hsl(var(--primary))]" />
                <span className="text-sm text-[hsl(var(--muted-foreground))]">
                  Generating sample…
                </span>
              </div>
            ) : previewRows.length > 0 ? (
              <div className="sk-table-shell">
                <table className="sk-table">
                  <thead>
                    <tr>
                      {previewCols.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, ri) => (
                      <tr key={ri}>
                        {previewCols.map((col) => (
                          <td key={col}>
                            {row[col] == null ? (
                              <span className="italic text-[hsl(var(--muted-foreground))]">
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
              <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-[hsl(var(--border))] text-sm text-[hsl(var(--muted-foreground))]">
                No preview data yet — click Regenerate.
              </div>
            )}

            {/* Quick‑adjust cards */}
            <div className="mt-8">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                  Quick Adjustments
                </h2>
                <button
                  type="button"
                  disabled={isRefreshing}
                  onClick={() => void handleRegenerate()}
                  className="sk-btn sk-btn-muted px-3 py-1.5 text-xs"
                >
                  {isRefreshing ? "…" : "↺ Apply & Regenerate"}
                </button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
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
          <div className="studio-card">
            {generatedFiles.length === 0 ? (
              <>
                <header className="mb-8">
                  <h1 className="font-[var(--font-title)] text-3xl font-black tracking-tight">
                    Generate Your Dataset
                  </h1>
                  <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                    Choose how many rows you need and which formats to export.
                    We&apos;ll generate and prepare your download.
                  </p>
                </header>

                <div className="grid max-w-xl gap-7">
                  {/* Row count */}
                  <div className="studio-field">
                    <span className="studio-label">Number of Rows</span>
                    <div className="mt-1 flex items-center gap-4">
                      <input
                        type="range"
                        min={100}
                        max={100000}
                        step={100}
                        value={rowCount}
                        onChange={(e) => setRowCount(Number(e.target.value))}
                        className="flex-1 accent-[hsl(var(--primary))]"
                      />
                      <input
                        type="number"
                        min={1}
                        max={10000000}
                        className="sk-input w-28 text-center font-semibold"
                        value={rowCount}
                        onChange={(e) =>
                          setRowCount(Math.max(1, Number(e.target.value) || 1))
                        }
                      />
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {rowCount.toLocaleString()} rows will be generated
                    </p>
                  </div>

                  {/* Format selection */}
                  <div className="studio-field">
                    <span className="studio-label">Output Format</span>
                    <div className="mt-1 flex flex-wrap gap-3">
                      {FORMAT_OPTIONS.map(({ value, label, ext }) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => toggleFormat(value)}
                          className={`format-btn ${
                            formats.includes(value)
                              ? "format-btn-active"
                              : "format-btn-inactive"
                          }`}
                        >
                          <span className="text-xl leading-none">
                            {value === "csv"
                              ? "⊞"
                              : value === "json"
                                ? "{ }"
                                : "⊟"}
                          </span>
                          <span className="font-bold">{label}</span>
                          <span className="text-xs opacity-60">{ext}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setStep(3)}
                      className="sk-btn sk-btn-muted"
                    >
                      ← Back to Preview
                    </button>
                    <button
                      type="button"
                      disabled={busy || formats.length === 0}
                      onClick={() => void handleGenerate()}
                      className="sk-btn sk-btn-primary px-8 py-3 text-base"
                    >
                      {busy ? (
                        <span className="flex items-center gap-2">
                          <span className="sk-spinner h-4 w-4" /> Generating…
                        </span>
                      ) : (
                        `Generate ${rowCount.toLocaleString()} Rows`
                      )}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* Success state */
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-700">
                    ✓
                  </div>
                  <div>
                    <h2 className="font-[var(--font-title)] text-2xl font-bold">
                      Dataset Ready!
                    </h2>
                    <p className="text-[hsl(var(--muted-foreground))]">
                      {rowCount.toLocaleString()} rows · {attrs.length} columns
                      · {generatedFiles.length}{" "}
                      {generatedFiles.length === 1 ? "file" : "files"}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {generatedFiles.map((file) => (
                    <div
                      key={file.format}
                      className="sk-panel flex items-center justify-between gap-3 p-4"
                    >
                      <div>
                        <p className="font-bold uppercase">{file.format}</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">
                          {formatBytes(file.size_bytes)}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDownload(file.format)}
                        className="sk-btn sk-btn-primary px-4 py-1.5 text-xs"
                      >
                        ↓ Download
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setGeneratedFiles([]);
                      setRowCount(1000);
                      setFormats(["csv"]);
                    }}
                    className="sk-btn sk-btn-muted"
                  >
                    Generate Again
                  </button>
                  <Link href="/dashboard" className="sk-btn sk-btn-primary">
                    Back to Dashboard
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Attribute Card (Step 2) ──────────────────────────────────────────────────

interface AttrCardProps {
  attr: AttrRow;
  index: number;
  total: number;
  onUpdate: <K extends keyof AttrRow>(
    i: number,
    key: K,
    val: AttrRow[K],
  ) => void;
  onRemove: (i: number) => void;
}

function AttrCard({ attr, index, total, onUpdate, onRemove }: AttrCardProps) {
  const showDist = DIST_TYPES.includes(attr.type);
  const showMinMax = NUMERIC_TYPES.includes(attr.type);
  const showCats = attr.type === "categorical";
  const showDates = attr.type === "date";

  return (
    <div className="attr-card">
      {/* Header row */}
      <div className="attr-card-header">
        <span className="attr-index-badge">{index + 1}</span>
        <input
          className="attr-name-input"
          value={attr.name}
          placeholder="field_name"
          onChange={(e) => onUpdate(index, "name", e.target.value)}
          spellCheck={false}
        />
        <select
          className="attr-type-pill ml-auto"
          value={attr.type}
          onChange={(e) => onUpdate(index, "type", e.target.value as DataType)}
        >
          {TYPE_OPTIONS.map(({ value, label, icon }) => (
            <option key={value} value={value}>
              {icon} {label}
            </option>
          ))}
        </select>
        {total > 1 && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="attr-remove-btn"
            aria-label={`Remove ${attr.name}`}
          >
            ✕
          </button>
        )}
      </div>

      {/* Body */}
      <div className="attr-card-body">
        {/* Description */}
        <input
          className="sk-input text-sm"
          placeholder="Describe this field — e.g. 'Patient age in years, range 18–90'"
          value={attr.description}
          onChange={(e) => onUpdate(index, "description", e.target.value)}
        />

        {/* Distribution + Null row */}
        <div className="attr-settings-row">
          {showDist && (
            <div className="attr-field-half">
              <label className="studio-label-xs">Distribution</label>
              <select
                className="sk-select text-sm"
                value={attr.distribution}
                onChange={(e) =>
                  onUpdate(
                    index,
                    "distribution",
                    e.target.value as DistributionType,
                  )
                }
              >
                {DIST_OPTIONS.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="attr-field-half">
            <label className="studio-label-xs flex items-center gap-2">
              <input
                type="checkbox"
                checked={attr.allow_nulls}
                onChange={(e) =>
                  onUpdate(index, "allow_nulls", e.target.checked)
                }
                className="accent-[hsl(var(--primary))]"
              />
              Allow Null Values
            </label>
            {attr.allow_nulls && (
              <div className="mt-2 flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={attr.null_percentage}
                  onChange={(e) =>
                    onUpdate(index, "null_percentage", Number(e.target.value))
                  }
                  className="flex-1 accent-[hsl(var(--primary))]"
                />
                <span className="w-10 text-right text-sm font-semibold">
                  {attr.null_percentage}%
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Min / Max */}
        {showMinMax && (
          <div className="attr-settings-row">
            <div className="attr-field-half">
              <label className="studio-label-xs">Min value</label>
              <input
                type="number"
                className="sk-input text-sm"
                placeholder="0"
                value={attr.min}
                onChange={(e) => onUpdate(index, "min", e.target.value)}
              />
            </div>
            <div className="attr-field-half">
              <label className="studio-label-xs">Max value</label>
              <input
                type="number"
                className="sk-input text-sm"
                placeholder="100"
                value={attr.max}
                onChange={(e) => onUpdate(index, "max", e.target.value)}
              />
            </div>
          </div>
        )}

        {/* Categories */}
        {showCats && (
          <div className="studio-field">
            <label className="studio-label-xs">
              Categories{" "}
              <span className="normal-case font-normal text-[hsl(var(--muted-foreground))]">
                — comma separated
              </span>
            </label>
            <input
              className="sk-input text-sm"
              placeholder="Male, Female, Non-binary, Prefer not to say"
              value={attr.categories}
              onChange={(e) => onUpdate(index, "categories", e.target.value)}
            />
          </div>
        )}

        {/* Date range */}
        {showDates && (
          <div className="attr-settings-row">
            <div className="attr-field-half">
              <label className="studio-label-xs">Start date</label>
              <input
                type="date"
                className="sk-input text-sm"
                value={attr.start_date}
                onChange={(e) => onUpdate(index, "start_date", e.target.value)}
              />
            </div>
            <div className="attr-field-half">
              <label className="studio-label-xs">End date</label>
              <input
                type="date"
                className="sk-input text-sm"
                value={attr.end_date}
                onChange={(e) => onUpdate(index, "end_date", e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Quick‑Adjust Card (Step 3) ───────────────────────────────────────────────

interface QuickAdjustProps {
  attr: AttrRow;
  index: number;
  onUpdate: <K extends keyof AttrRow>(
    i: number,
    key: K,
    val: AttrRow[K],
  ) => void;
}

function QuickAdjustCard({ attr, index, onUpdate }: QuickAdjustProps) {
  const showMinMax = NUMERIC_TYPES.includes(attr.type);
  const showCats = attr.type === "categorical";

  return (
    <div className="sk-panel space-y-3 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-semibold text-sm">{attr.name}</span>
        <span className="sk-chip flex-shrink-0">{typeLabel(attr.type)}</span>
      </div>

      {/* Null toggle */}
      <label className="flex cursor-pointer items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
        <input
          type="checkbox"
          checked={attr.allow_nulls}
          onChange={(e) => onUpdate(index, "allow_nulls", e.target.checked)}
          className="accent-[hsl(var(--primary))]"
        />
        Nulls{" "}
        {attr.allow_nulls && (
          <span className="font-semibold text-[hsl(var(--foreground))]">
            {attr.null_percentage}%
          </span>
        )}
      </label>

      {attr.allow_nulls && (
        <input
          type="range"
          min={1}
          max={50}
          value={attr.null_percentage}
          onChange={(e) =>
            onUpdate(index, "null_percentage", Number(e.target.value))
          }
          className="w-full accent-[hsl(var(--primary))]"
        />
      )}

      {showMinMax && (
        <div className="flex gap-2">
          <input
            type="number"
            className="sk-input py-1 text-xs"
            placeholder="Min"
            value={attr.min}
            onChange={(e) => onUpdate(index, "min", e.target.value)}
          />
          <input
            type="number"
            className="sk-input py-1 text-xs"
            placeholder="Max"
            value={attr.max}
            onChange={(e) => onUpdate(index, "max", e.target.value)}
          />
        </div>
      )}

      {showCats && (
        <input
          className="sk-input py-1 text-xs"
          placeholder="cat1, cat2, cat3"
          value={attr.categories}
          onChange={(e) => onUpdate(index, "categories", e.target.value)}
        />
      )}
    </div>
  );
}
