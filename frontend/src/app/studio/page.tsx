"use client";

import Link from "next/link";
import { CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Download,
  HelpCircle,
  Keyboard,
  LoaderCircle,
  Menu,
  Plus,
  Search,
  X,
} from "lucide-react";
import { List } from "react-window";

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
  type PreviewColumnComparison,
  createDataset,
  downloadDatasetFile,
  generationPreflight,
  generateDataset,
  getDatasetVersions,
  listDatasetTemplates,
  listDatasetFiles,
  previewDataset,
  saveAttributes,
  type GenerationPreflightResponse,
} from "@/lib/api-client";

import { ValidationDashboard } from "@/components/studio/validation-dashboard";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { useFeedback } from "@/components/ui/feedback-provider";
import { useErrorNotifier } from "@/lib/use-error-notifier";
import { KeyboardShortcutsModal } from "@/components/keyboard-shortcuts-modal";
import {
  StudioCommandPalette,
  StudioCommandGroup,
  StudioCommandItem,
} from "@/components/studio-command-palette";

const ASYNC_POLL_INTERVAL_MS = 1500;
const ASYNC_POLL_MAX_ATTEMPTS = 1200;
const AUTO_ASYNC_ROW_THRESHOLD = 50000;
const AUTO_ASYNC_CELL_THRESHOLD = 1000000;
const PREVIEW_ROW_HEIGHT = 44;

// ─── Helper Functions ─────────────────────────────────────────────────────

function templateColumnsToAttrRows(columns: Record<string, any>): AttrRow[] {
  return Object.entries(columns).map(([name, colConfig]) => {
    const dist = colConfig.distribution || {};
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

    // Map data_type to field type
    let fieldType: AttrRow["type"] = "text";
    if (colConfig.data_type === "integer") fieldType = "integer";
    else if (colConfig.data_type === "float") fieldType = "float";
    else if (colConfig.data_type === "boolean") fieldType = "boolean";
    else if (colConfig.data_type === "date") fieldType = "date";
    else if (colConfig.data_type === "email") fieldType = "email";
    else if (colConfig.data_type === "categorical") fieldType = "categorical";
    else if (colConfig.data_type === "text") fieldType = "text";

    const row: AttrRow = makeRow({
      name,
      type: fieldType,
    });

    // Apply distribution settings
    if (dist.max_length) row.max_length = String(dist.max_length);
    if (dist.min !== undefined) row.min = String(dist.min);
    if (dist.max !== undefined) row.max = String(dist.max);
    if (dist.start_date) row.start_date = dist.start_date;
    if (dist.end_date) row.end_date = dist.end_date;
    if (dist.precision) row.precision = String(dist.precision);

    // Handle categorical
    if (dist.categories && Array.isArray(dist.categories)) {
      row.categories = dist.categories.join(", ");
      row.distribution = "weighted_categorical";
      if (dist.probabilities && Array.isArray(dist.probabilities)) {
        row.weights = dist.probabilities.join(", ");
      }
    }

    return row;
  });
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function StudioPage() {
  const router = useRouter();
  const { pushToast } = useFeedback();
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [keyboardHelpOpen, setKeyboardHelpOpen] = useState(false);
  const [optimisticSaving, setOptimisticSaving] = useState(false);

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
  const [previewComparisonCols, setPreviewComparisonCols] = useState<
    PreviewColumnComparison[]
  >([]);
  const [selectedComparisonCol, setSelectedComparisonCol] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const optimisticSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const optimisticSaveSeq = useRef(0);

  // Step 4
  const [rowCount, setRowCount] = useState(1000);
  const [formats, setFormats] = useState<OutputFormat[]>(["csv"]);
  const [seed, setSeed] = useState("");
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileInfo[]>([]);
  const [qualityReport, setQualityReport] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [qualityDashboard, setQualityDashboard] = useState<{
    overall_score: number;
    metrics: {
      distribution_fidelity: number;
      relationship_integrity: number;
      null_pattern_match: number;
      uniqueness: number;
      freshness: number;
    };
    warnings: string[];
    recommendations: string[];
  } | null>(null);
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
  const [validationSummary, setValidationSummary] = useState<any>(null);
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
  const [preflightResult, setPreflightResult] =
    useState<GenerationPreflightResponse | null>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [allowLowQualityDownloads, setAllowLowQualityDownloads] =
    useState(false);
  const { notifyError } = useErrorNotifier(setError);

  const estimatedCells = rowCount * Math.max(1, attrs.length);
  const useAsyncGeneration =
    rowCount >= AUTO_ASYNC_ROW_THRESHOLD ||
    estimatedCells >= AUTO_ASYNC_CELL_THRESHOLD;
  const shouldUseAsyncGeneration =
    useAsyncGeneration || Boolean(preflightResult?.requires_async);
  const guardrailsPassed =
    qualityGuardrails == null
      ? true
      : Boolean((qualityGuardrails as { passed?: boolean }).passed);

  const selectedPreviewComparison =
    previewComparisonCols.find(
      (item) => item.column === selectedComparisonCol,
    ) ??
    previewComparisonCols[0] ??
    null;
  const selectedNumericComparison = selectedPreviewComparison?.numeric ?? null;
  const previewColumnTemplate = useMemo(
    () => `repeat(${Math.max(previewCols.length, 1)}, minmax(140px, 1fr))`,
    [previewCols.length],
  );
  const renderPreviewRow = ({
    index,
    style,
  }: {
    index?: number;
    style?: CSSProperties;
    [key: string]: unknown;
  }) => {
    const safeIndex = typeof index === "number" ? index : 0;
    const row = previewRows[safeIndex] ?? {};
    return (
      <div
        style={{
          ...style,
          display: "grid",
          gridTemplateColumns: previewColumnTemplate,
        }}
        className="border-b border-border/40 text-sm transition-colors hover:bg-card/70"
      >
        {previewCols.map((col) => (
          <div
            key={`${safeIndex}-${col}`}
            className="truncate px-4 py-2.5 text-foreground"
          >
            {row[col] == null ? (
              <span className="italic text-muted-foreground/60">null</span>
            ) : (
              String(row[col])
            )}
          </div>
        ))}
      </div>
    );
  };

  // Load existing dataset from query string
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    if (params.get("new") === "true") {
      localStorage.removeItem("datasim:dataset_id");
      localStorage.removeItem("datasim:dataset_version_id");
      localStorage.removeItem("datasim:validation_summary");

      setDatasetId("");
      setVersionId("");
      setGeneratedFiles([]);
      setAttrs([newAttr(0)]);

      const selectedTemplateId = params.get("template");
      if (selectedTemplateId) {
        void listDatasetTemplates()
          .then((response) => {
            const selectedTemplate = response.templates.find(
              (template) => template.id === selectedTemplateId,
            );
            if (selectedTemplate?.columns) {
              setAttrs(templateColumnsToAttrRows(selectedTemplate.columns));
            }
          })
          .catch(() => {
            setError("Failed to load selected template.");
          });
      }

      const newUrl = window.location.pathname;
      window.history.replaceState({}, document.title, newUrl);
      return;
    }

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

  const scheduleOptimisticValidation = (
    nextAttrs: AttrRow[],
    previousAttrs: AttrRow[],
  ) => {
    if (step !== 3 || !datasetId) {
      return;
    }

    if (optimisticSaveTimer.current) {
      clearTimeout(optimisticSaveTimer.current);
      optimisticSaveTimer.current = null;
    }

    const seq = optimisticSaveSeq.current + 1;
    optimisticSaveSeq.current = seq;
    setOptimisticSaving(true);

    optimisticSaveTimer.current = setTimeout(() => {
      void (async () => {
        try {
          const correlations = parseCorrelationRules();
          const res = await saveAttributes({
            dataset_id: datasetId,
            attributes: nextAttrs.map(toApiAttr),
            seed: seed.trim() ? Number(seed) : undefined,
            correlations,
          });

          if (optimisticSaveSeq.current !== seq) {
            return;
          }

          setVersionId(res.version_id);
          localStorage.setItem("datasim:dataset_version_id", res.version_id);
          await loadPreview(res.version_id);
          pushToast({
            title: "Changes Synced",
            message: "Field updates validated and preview refreshed.",
            intent: "success",
          });
        } catch (e) {
          if (optimisticSaveSeq.current !== seq) {
            return;
          }
          setAttrs(previousAttrs);
          notifyError(
            "Validation Failed",
            e,
            "Field update was rejected. Reverting to previous values.",
          );
        } finally {
          if (optimisticSaveSeq.current === seq) {
            setOptimisticSaving(false);
          }
        }
      })();
    }, 700);
  };

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

      if (event.key === "Escape") {
        setCommandPaletteOpen(false);
        setKeyboardHelpOpen(false);
        setMobileSidebarOpen(false);
        return;
      }

      if (!isModifier) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === "k") {
        event.preventDefault();
        setCommandPaletteOpen(true);
        return;
      }
      if (key === "/") {
        event.preventDefault();
        setKeyboardHelpOpen(true);
        return;
      }
      if (isAltShortcut && key === "n" && !isTypingTarget) {
        event.preventDefault();
        router.push("/studio?new=true");
        return;
      }
      if (
        key === "e" &&
        !isTypingTarget &&
        step === 4 &&
        generatedFiles.length > 0
      ) {
        event.preventDefault();
        void handleDownload(generatedFiles[0].format);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [generatedFiles, router, step]);

  useEffect(() => {
    return () => {
      if (optimisticSaveTimer.current) {
        clearTimeout(optimisticSaveTimer.current);
      }
    };
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
      notifyError("Create Dataset Failed", e, "Failed to create dataset");
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
      notifyError("Save Attributes Failed", e, "Failed to save attributes");
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

      const nextComparisonCols = res.comparison?.columns ?? [];
      setPreviewComparisonCols(nextComparisonCols);
      if (nextComparisonCols.length === 0) {
        setSelectedComparisonCol("");
      } else {
        const selectedStillExists = nextComparisonCols.some(
          (item) => item.column === selectedComparisonCol,
        );
        if (!selectedStillExists) {
          setSelectedComparisonCol(nextComparisonCols[0].column);
        }
      }
    } catch (e) {
      notifyError("Preview Failed", e, "Preview failed");
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
      };

      if (!shouldUseAsyncGeneration) {
        setAllowLowQualityDownloads(false);
        const res = await generateDataset(payload);
        setGeneratedFiles(res.files);
        setQualityReport(
          (res.quality_report as Record<string, unknown>) ?? null,
        );
        setQualityDashboard(res.quality_dashboard ?? null);
        setValidationSummary(res.validation_summary ?? null);
        if (res.validation_summary) {
          try {
            localStorage.setItem(
              "datasim:validation_summary",
              JSON.stringify(res.validation_summary),
            );
          } catch {
            /* ignore */
          }
        }
        setQualityGuardrails(
          (res.quality_guardrails as Record<string, unknown>) ?? null,
        );
        setGenerationSignature(res.generation_signature ?? "");
        setGenerationRunId(res.generation_run_id ?? "");
        setRunComparison((res.comparison as Record<string, unknown>) ?? null);
        return;
      }

      const queued = await generateDatasetAsync(payload);
      setAllowLowQualityDownloads(false);
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
          setQualityDashboard(result.quality_dashboard ?? null);
          setValidationSummary(result.validation_summary ?? null);
          if (result.validation_summary) {
            try {
              localStorage.setItem(
                "datasim:validation_summary",
                JSON.stringify(result.validation_summary),
              );
            } catch {
              /* ignore */
            }
          }
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
      notifyError("Generation Failed", e, "Generation failed");
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
      notifyError("Cancel Job Failed", e, "Failed to cancel job");
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
      notifyError("Download Failed", e, "Download failed");
    }
  };

  useEffect(() => {
    if (step !== 4 || !datasetId || formats.length === 0) {
      return;
    }

    let isCancelled = false;
    setPreflightBusy(true);

    void generationPreflight({
      dataset_id: datasetId,
      dataset_version_id: versionId || undefined,
      row_count: rowCount,
      formats,
      seed: seed.trim() ? Number(seed) : undefined,
    })
      .then((response) => {
        if (!isCancelled) {
          setPreflightResult(response);
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setPreflightResult(null);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setPreflightBusy(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [
    step,
    datasetId,
    versionId,
    rowCount,
    formats,
    seed,
    driftEnabled,
    driftIntensity,
    driftColumnsText,
  ]);

  // ── Attribute helpers ────────────────────────────────────────
  const updateAttr = <K extends keyof AttrRow>(
    i: number,
    key: K,
    value: AttrRow[K],
  ) => {
    setAttrs((prev) => {
      const updated = prev.map((a, idx) => {
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
      });

      scheduleOptimisticValidation(updated, prev);
      return updated;
    });
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
                  className={`group flex min-h-12 w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium transition-colors ${
                    active
                      ? "bg-primary/10 text-primary"
                      : done
                        ? "text-muted-foreground hover:bg-card/70 hover:text-foreground"
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
              <div className="rounded-lg border border-border bg-card/70 p-3">
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

        {mobileSidebarOpen && (
          <button
            type="button"
            className="fixed inset-0 z-40 bg-card/70 md:hidden"
            aria-label="Close steps menu"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}

        <aside
          className={`fixed left-0 top-0 z-50 h-full w-80 max-w-[85vw] transform border-r border-border bg-background p-4 transition-transform md:hidden ${
            mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
          aria-hidden={!mobileSidebarOpen}
        >
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
              Steps
            </p>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-12 w-12"
              onClick={() => setMobileSidebarOpen(false)}
              aria-label="Close steps drawer"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <nav className="space-y-1">
            {STEP_LABELS.map(([num, label], i) => {
              const s = (i + 1) as Step;
              const done = step > s;
              const active = step === s;
              const inactive = s > step;
              return (
                <button
                  key={`mobile-step-${s}`}
                  type="button"
                  disabled={inactive}
                  onClick={() => {
                    if (done) {
                      setStep(s);
                      setMobileSidebarOpen(false);
                    }
                  }}
                  className={`group flex min-h-12 w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium transition-colors ${
                    active
                      ? "bg-primary/10 text-primary"
                      : done
                        ? "text-muted-foreground hover:bg-card/70 hover:text-foreground"
                        : "cursor-not-allowed text-muted-foreground/50"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      active
                        ? "bg-primary text-primary-foreground"
                        : done
                          ? "bg-green-500/20 text-green-400"
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
        </aside>

        {/* ── Main Content ── */}
        <div className="min-w-0 flex-1 pb-24">
          {/* Mobile step bar */}
          <div className="mb-6 md:hidden">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                Step {step} of {STEP_LABELS.length}
              </p>
              <Button
                type="button"
                variant="outline"
                className="h-12 gap-2 px-3"
                onClick={() => setMobileSidebarOpen(true)}
              >
                <Menu className="h-4 w-4" />
                Steps
              </Button>
            </div>
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
            <Alert variant="destructive" className="mb-6">
              <AlertTriangle className="h-5 w-5" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                <button
                  type="button"
                  onClick={() => setError("")}
                  className="rounded-full p-1 transition-colors hover:bg-destructive/20"
                  aria-label="Dismiss error"
                >
                  <X className="h-4 w-4" />
                </button>
              </AlertDescription>
            </Alert>
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
                <Button
                  type="button"
                  variant="default"
                  disabled={busy || !dsName.trim()}
                  onClick={() => void handleCreate()}
                >
                  {busy ? (
                    <span className="flex items-center justify-center gap-2">
                      <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                      Creating…
                    </span>
                  ) : (
                    "Create & Define Fields →"
                  )}
                </Button>
                <Button asChild variant="outline">
                  <Link href="/dashboard">Cancel</Link>
                </Button>
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
                <Button
                  type="button"
                  variant="default"
                  className="whitespace-nowrap"
                  disabled={busy || attrs.length === 0}
                  onClick={() => void handleSaveAndPreview()}
                >
                  {busy ? (
                    <span className="flex items-center justify-center gap-2">
                      <LoaderCircle className="h-4 w-4 animate-spin" /> Saving…
                    </span>
                  ) : (
                    "Save & Preview →"
                  )}
                </Button>
              </header>

              <Card className="mb-8 p-4 bg-card/70 border-border">
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
              </Card>

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
                <Button
                  type="button"
                  variant="default"
                  disabled={busy || attrs.length === 0}
                  onClick={() => void handleSaveAndPreview()}
                >
                  {busy ? "Saving…" : "Save & Preview →"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setStep(1)}
                >
                  ← Back
                </Button>
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
                  {optimisticSaving && (
                    <p className="mt-2 flex items-center gap-2 text-xs text-cyan-300">
                      <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                      Validating field changes and refreshing preview...
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="min-h-12"
                    onClick={() => setStep(2)}
                  >
                    ← Edit Fields
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="min-h-12"
                    disabled={isRefreshing}
                    onClick={() => void handleRegenerate()}
                  >
                    {isRefreshing ? (
                      <span className="flex items-center gap-2">
                        <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                        Regenerating…
                      </span>
                    ) : (
                      "↺ Regenerate"
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="default"
                    className="min-h-12"
                    onClick={() => setStep(4)}
                  >
                    Looks Good →
                  </Button>
                </div>
              </header>

              {realismMetadata && (
                <Card className="mb-6 border-border bg-card/70 p-4">
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
                </Card>
              )}

              {previewComparisonCols.length > 0 && (
                <Card className="mb-6 border-border bg-card/70 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        Statistical Comparison
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Expected distribution versus synthetic preview sample.
                      </p>
                    </div>
                    <select
                      className="h-9 min-w-48 rounded-md border border-border bg-background px-3 text-sm"
                      value={selectedPreviewComparison?.column ?? ""}
                      onChange={(e) => setSelectedComparisonCol(e.target.value)}
                    >
                      {previewComparisonCols.map((column) => (
                        <option key={column.column} value={column.column}>
                          {column.column}
                        </option>
                      ))}
                    </select>
                  </div>

                  {selectedNumericComparison ? (
                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <div className="rounded-lg border border-border/60 bg-background/60 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          Summary
                        </p>
                        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-muted-foreground">
                              Expected range:
                            </span>{" "}
                            {selectedNumericComparison.expected_min?.toFixed(
                              2,
                            ) ?? "n/a"}{" "}
                            -{" "}
                            {selectedNumericComparison.expected_max?.toFixed(
                              2,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Synthetic range:
                            </span>{" "}
                            {selectedNumericComparison.synthetic_min?.toFixed(
                              2,
                            ) ?? "n/a"}{" "}
                            -{" "}
                            {selectedNumericComparison.synthetic_max?.toFixed(
                              2,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Expected mean:
                            </span>{" "}
                            {selectedNumericComparison.expected_mean?.toFixed(
                              3,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Synthetic mean:
                            </span>{" "}
                            {selectedNumericComparison.synthetic_mean?.toFixed(
                              3,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Expected skew:
                            </span>{" "}
                            {selectedNumericComparison.expected_skewness?.toFixed(
                              3,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Synthetic skew:
                            </span>{" "}
                            {selectedNumericComparison.synthetic_skewness?.toFixed(
                              3,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Expected kurtosis:
                            </span>{" "}
                            {selectedNumericComparison.expected_kurtosis?.toFixed(
                              3,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Synthetic kurtosis:
                            </span>{" "}
                            {selectedNumericComparison.synthetic_kurtosis?.toFixed(
                              3,
                            ) ?? "n/a"}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Expected null %:
                            </span>{" "}
                            {selectedNumericComparison.expected_missing_pct.toFixed(
                              2,
                            )}
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Synthetic null %:
                            </span>{" "}
                            {selectedNumericComparison.synthetic_missing_pct.toFixed(
                              2,
                            )}
                          </div>
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2 text-xs">
                          <span
                            className={`rounded-full px-2 py-1 ${
                              selectedNumericComparison.ks_passed
                                ? "bg-emerald-500/15 text-emerald-300"
                                : "bg-amber-500/15 text-amber-200"
                            }`}
                          >
                            KS:{" "}
                            {selectedNumericComparison.ks_p_value?.toFixed(3) ??
                              "n/a"}
                          </span>
                          <span
                            className={`rounded-full px-2 py-1 ${
                              selectedNumericComparison.ad_passed
                                ? "bg-emerald-500/15 text-emerald-300"
                                : "bg-amber-500/15 text-amber-200"
                            }`}
                          >
                            AD:{" "}
                            {selectedNumericComparison.ad_significance_level?.toFixed(
                              2,
                            ) ?? "n/a"}
                            %
                          </span>
                          {selectedNumericComparison.low_variance && (
                            <span className="rounded-full bg-amber-500/15 px-2 py-1 text-amber-200">
                              Low variance detected
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="rounded-lg border border-border/60 bg-background/60 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          Histogram Overlay
                        </p>
                        <div className="mt-3 space-y-2">
                          {selectedNumericComparison.histogram_bins.length >
                          0 ? (
                            selectedNumericComparison.histogram_bins.map(
                              (bin, index, all) => {
                                const maxCount = Math.max(
                                  1,
                                  ...all.map((entry) =>
                                    Math.max(
                                      entry.expected_count,
                                      entry.synthetic_count,
                                    ),
                                  ),
                                );
                                const expectedWidth =
                                  (bin.expected_count / maxCount) * 100;
                                const syntheticWidth =
                                  (bin.synthetic_count / maxCount) * 100;
                                return (
                                  <div
                                    key={`${bin.bin_start}-${bin.bin_end}-${index}`}
                                  >
                                    <div className="mb-1 flex items-center justify-between text-[11px] text-muted-foreground">
                                      <span>
                                        {bin.bin_start.toFixed(1)} -{" "}
                                        {bin.bin_end.toFixed(1)}
                                      </span>
                                      <span>
                                        E {bin.expected_count.toFixed(0)} / S{" "}
                                        {bin.synthetic_count.toFixed(0)}
                                      </span>
                                    </div>
                                    <div className="relative h-3 rounded bg-border/40">
                                      <div
                                        className="absolute left-0 top-0 h-3 rounded bg-cyan-400/50"
                                        style={{ width: `${expectedWidth}%` }}
                                      />
                                      <div
                                        className="absolute left-0 top-0 h-2 rounded bg-amber-300/70"
                                        style={{ width: `${syntheticWidth}%` }}
                                      />
                                    </div>
                                  </div>
                                );
                              },
                            )
                          ) : (
                            <p className="text-xs text-muted-foreground">
                              Not enough data to render histogram bins.
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-3 text-xs text-muted-foreground">
                      Detailed statistical comparison is currently available for
                      numeric columns.
                    </p>
                  )}
                </Card>
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
                <div className="space-y-3">
                  <div className="text-xs text-muted-foreground">
                    {previewRows.length.toLocaleString()} rows ·{" "}
                    {previewCols.length} columns
                  </div>

                  <div className="space-y-3 md:hidden">
                    {previewRows.slice(0, 60).map((row, index) => (
                      <Card
                        key={`preview-card-${index}`}
                        className="border-border bg-background/60 p-3"
                      >
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          Row {index + 1}
                        </p>
                        <div className="space-y-1.5 text-sm">
                          {previewCols.map((col) => (
                            <div
                              key={`preview-card-${index}-${col}`}
                              className="flex items-start justify-between gap-3"
                            >
                              <span className="min-w-0 flex-1 text-xs text-muted-foreground">
                                {col}
                              </span>
                              <span className="min-w-0 flex-1 truncate text-right text-foreground">
                                {row[col] == null ? "null" : String(row[col])}
                              </span>
                            </div>
                          ))}
                        </div>
                      </Card>
                    ))}
                  </div>

                  <div className="hidden rounded-lg border border-border md:block">
                    <div className="max-h-[460px] overflow-auto">
                      <div
                        className="sticky top-0 z-10 grid border-b border-border/50 bg-background/95"
                        style={{ gridTemplateColumns: previewColumnTemplate }}
                      >
                        {previewCols.map((col) => (
                          <div
                            key={`preview-header-${col}`}
                            className="truncate px-4 py-3 text-left text-sm font-medium text-muted-foreground"
                          >
                            {col}
                          </div>
                        ))}
                      </div>
                      <List
                        style={{
                          height: Math.min(
                            420,
                            Math.max(
                              220,
                              previewRows.length * PREVIEW_ROW_HEIGHT,
                            ),
                          ),
                          width: "100%",
                        }}
                        rowCount={previewRows.length}
                        rowHeight={PREVIEW_ROW_HEIGHT}
                        rowComponent={renderPreviewRow}
                        rowProps={{}}
                      />
                    </div>
                  </div>
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
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="h-9 px-3 text-xs"
                    disabled={isRefreshing}
                    onClick={() => void handleRegenerate()}
                  >
                    {isRefreshing ? "…" : "↺ Apply & Regenerate"}
                  </Button>
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
                                : "border-border bg-card/70 text-muted-foreground hover:border-primary/50 hover:bg-primary/5"
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

                    <div className="space-y-3 rounded-lg border border-border bg-card/70 p-4">
                      <p className="text-sm font-medium text-foreground">
                        Generation mode:{" "}
                        {shouldUseAsyncGeneration
                          ? "Background job"
                          : "Immediate"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Auto-selected by thresholds (
                        {AUTO_ASYNC_ROW_THRESHOLD.toLocaleString()} rows or{" "}
                        {AUTO_ASYNC_CELL_THRESHOLD.toLocaleString()} estimated
                        cells).
                      </p>

                      {(preflightBusy || preflightResult?.issues?.length) && (
                        <div className="rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
                          {preflightBusy ? (
                            <p>Running preflight checks...</p>
                          ) : (
                            <>
                              <p className="font-medium text-foreground">
                                Preflight checks
                              </p>
                              {preflightResult?.issues?.length ? (
                                <ul className="mt-1 space-y-1">
                                  {preflightResult.issues.map((issue) => (
                                    <li key={`${issue.code}-${issue.message}`}>
                                      {issue.message}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="mt-1">
                                  No blocking risks detected.
                                </p>
                              )}
                            </>
                          )}
                        </div>
                      )}

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

                    <div className="space-y-3 rounded-lg border border-border bg-card/70 p-4">
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
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setStep(3)}
                      >
                        ← Back to Preview
                      </Button>
                      <Button
                        type="button"
                        variant="default"
                        disabled={busy || formats.length === 0}
                        onClick={() => void handleGenerate()}
                      >
                        {busy ? (
                          <span className="flex items-center justify-center gap-2">
                            <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                            Generating…
                          </span>
                        ) : (
                          `Generate ${rowCount.toLocaleString()} Rows`
                        )}
                      </Button>
                      {shouldUseAsyncGeneration && jobId && busy && (
                        <Button
                          type="button"
                          variant="outline"
                          className="border-amber-400/50 text-amber-200 hover:bg-amber-500/10 hover:text-amber-100"
                          onClick={() => void handleCancelJob()}
                        >
                          Cancel Job
                        </Button>
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
                        className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card/70 p-4"
                      >
                        <div>
                          <p className="font-bold uppercase">{file.format}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatBytes(file.size_bytes)}
                          </p>
                        </div>
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="h-9 px-3 text-xs"
                          disabled={
                            !guardrailsPassed && !allowLowQualityDownloads
                          }
                          onClick={() => void handleDownload(file.format)}
                        >
                          <Download className="mr-1.5 h-3 w-3" />
                          Download
                        </Button>
                      </div>
                    ))}
                  </div>

                  {!guardrailsPassed && (
                    <Alert>
                      <AlertTriangle className="h-5 w-5" />
                      <AlertDescription className="space-y-2">
                        <p>
                          Quality guardrails reported warnings above threshold.
                          Review diagnostics before downloading.
                        </p>
                        <label className="inline-flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            checked={allowLowQualityDownloads}
                            onChange={(e) =>
                              setAllowLowQualityDownloads(e.target.checked)
                            }
                          />
                          I understand the risk and want to download anyway.
                        </label>
                      </AlertDescription>
                    </Alert>
                  )}

                  {qualityDashboard && (
                    <Card className="border-border bg-card/70 p-4">
                      <h3 className="font-semibold text-foreground">
                        Data Quality Score Dashboard
                      </h3>
                      <div className="mt-3 grid gap-4 lg:grid-cols-[220px_1fr]">
                        <div className="rounded-lg border border-border/60 bg-background/40 p-4 text-center">
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            Overall Score
                          </p>
                          <p className="mt-2 text-4xl font-bold text-foreground">
                            {qualityDashboard.overall_score}
                            <span className="text-lg text-muted-foreground">
                              /100
                            </span>
                          </p>
                          <div className="mt-3 h-2 w-full rounded bg-border/50">
                            <div
                              className="h-2 rounded bg-emerald-400"
                              style={{
                                width: `${Math.max(0, Math.min(100, qualityDashboard.overall_score))}%`,
                              }}
                            />
                          </div>
                        </div>

                        <div className="space-y-3">
                          {[
                            [
                              "Distribution Fidelity",
                              qualityDashboard.metrics.distribution_fidelity,
                            ],
                            [
                              "Relationship Integrity",
                              qualityDashboard.metrics.relationship_integrity,
                            ],
                            [
                              "Null Pattern Match",
                              qualityDashboard.metrics.null_pattern_match,
                            ],
                            ["Uniqueness", qualityDashboard.metrics.uniqueness],
                            ["Freshness", qualityDashboard.metrics.freshness],
                          ].map(([label, value]) => (
                            <div key={String(label)}>
                              <div className="mb-1 flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">
                                  {String(label)}
                                </span>
                                <span className="font-medium text-foreground">
                                  {Number(value)}/100
                                </span>
                              </div>
                              <div className="h-2 rounded bg-border/50">
                                <div
                                  className="h-2 rounded bg-cyan-400"
                                  style={{
                                    width: `${Math.max(0, Math.min(100, Number(value)))}%`,
                                  }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {(qualityDashboard.warnings.length > 0 ||
                        qualityDashboard.recommendations.length > 0) && (
                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                          <div className="rounded border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-100">
                            <p className="font-semibold">Warnings</p>
                            {qualityDashboard.warnings.length > 0 ? (
                              <ul className="mt-2 space-y-1">
                                {qualityDashboard.warnings.map(
                                  (warning, index) => (
                                    <li key={`warn-${index}`}>- {warning}</li>
                                  ),
                                )}
                              </ul>
                            ) : (
                              <p className="mt-2">No warnings reported.</p>
                            )}
                          </div>

                          <div className="rounded border border-cyan-500/40 bg-cyan-500/10 p-3 text-xs text-cyan-100">
                            <p className="font-semibold">Recommendations</p>
                            {qualityDashboard.recommendations.length > 0 ? (
                              <ul className="mt-2 space-y-1">
                                {qualityDashboard.recommendations.map(
                                  (recommendation, index) => (
                                    <li key={`rec-${index}`}>
                                      - {recommendation}
                                    </li>
                                  ),
                                )}
                              </ul>
                            ) : (
                              <p className="mt-2">No action needed.</p>
                            )}
                          </div>
                        </div>
                      )}
                    </Card>
                  )}

                  {validationSummary && (
                    <ValidationDashboard report={validationSummary} />
                  )}

                  <div className="rounded-lg border border-border bg-card/70 p-4">
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
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setGeneratedFiles([]);
                        setQualityReport(null);
                        setQualityDashboard(null);
                        setQualityGuardrails(null);
                        setValidationSummary(null);
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
                    >
                      Generate Again
                    </Button>
                    <Button asChild variant="default">
                      <Link href="/dashboard">Back to Dashboard</Link>
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

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
              setKeyboardHelpOpen(true);
            }}
          >
            <Keyboard className="h-4 w-4 text-cyan-300" />
            Keyboard Shortcuts
          </StudioCommandItem>
          {step === 4 && generatedFiles.length > 0 && (
            <StudioCommandItem
              onSelect={() => {
                setCommandPaletteOpen(false);
                void handleDownload(generatedFiles[0].format);
              }}
            >
              <Download className="h-4 w-4 text-cyan-300" />
              Export Current Dataset
            </StudioCommandItem>
          )}
        </StudioCommandGroup>
      </StudioCommandPalette>

      {keyboardHelpOpen && (
        <KeyboardShortcutsModal
          open={keyboardHelpOpen}
          onClose={() => setKeyboardHelpOpen(false)}
          shortcuts={[
            { keys: "Cmd/Ctrl + K", description: "Open command palette" },
            { keys: "Alt + N", description: "Create new dataset" },
            {
              keys: "Cmd/Ctrl + E",
              description: "Export current dataset (Step 4)",
            },
            { keys: "Cmd/Ctrl + /", description: "Show keyboard help" },
            { keys: "Esc", description: "Close dialogs and menus" },
            {
              keys: "Tab / Enter",
              description: "Navigate and confirm controls",
            },
          ]}
        />
      )}
    </AuthGuard>
  );
}
