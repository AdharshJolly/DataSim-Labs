"use client";

import { CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  Download,
  HelpCircle,
  Keyboard,
  Menu,
  Plus,
  Search,
  X,
} from "lucide-react";

import { STEP_LABELS } from "@/components/studio/constants";
import {
  newAttr,
  uid,
  validateCategoricalWeights,
} from "@/components/studio/studio-helpers";
import {
  applySuggestionToAttr,
  attrRowToApiAttribute,
  templateColumnsToAttrRows,
} from "@/components/studio/attr-transform";
import { mergeSemanticRuleSets } from "@/components/studio/rule-parsers";
import type { AttrRow, OutputFormat, Step } from "@/components/studio/types";
import { Step1CreateDataset } from "@/components/studio/steps/step-1-create-dataset";
import { Step2DefineFields } from "@/components/studio/steps/step-2-define-fields";
import { Step3PreviewRefine } from "@/components/studio/steps/step-3-preview-refine";
import { Step4Generate } from "@/components/studio/steps/step-4-generate";
import { useStudioGenerationFlow } from "@/components/studio/hooks/use-studio-generation-flow";
import { useStudioRules } from "@/components/studio/hooks/use-studio-rules";
import {
  type AttributeConfig,
  type GeneratedFileInfo,
  type GenerationJobStatus,
  type PreviewColumnComparison,
  createDataset,
  generationPreflight,
  dryRunSemanticRules,
  getDatasetVersions,
  listDatasetTemplates,
  listDatasetFiles,
  previewDataset,
  explainDatasetRow,
  suggestDatasetSettings,
  compareDatasetOutput,
  saveAttributes,
  getSemanticRules,
  inferSemanticRules,
  upsertSemanticRules,
  type DryRunSemanticRulesResponse,
  type SemanticConflictPolicy,
  type SemanticRulesMetadata,
  type GenerationPreflightResponse,
  type ExplainResponse,
  type AttributeSuggestion,
  type CompareResponse,
} from "@/lib/api-client";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { useFeedback } from "@/components/ui/feedback-provider";
import { useErrorNotifier } from "@/lib/use-error-notifier";
import { KeyboardShortcutsModal } from "@/components/keyboard-shortcuts-modal";
import {
  StudioCommandPalette,
  StudioCommandGroup,
  StudioCommandItem,
} from "@/components/studio-command-palette";
import { useStudioShellState } from "@/app/studio/hooks/use-studio-shell-state";
import { resolveGenerationMode } from "@/app/studio/logic/generation-mode";
import { StudioErrorAlert } from "@/app/studio/ui/studio-error-alert";

const ASYNC_POLL_INTERVAL_MS = 1500;
const ASYNC_POLL_MAX_ATTEMPTS = 1200;
const AUTO_ASYNC_ROW_THRESHOLD = 50000;
const AUTO_ASYNC_CELL_THRESHOLD = 1000000;
const PREVIEW_ROW_HEIGHT = 44;

// ─── Main Component ───────────────────────────────────────────────────────────

export default function StudioPage() {
  const router = useRouter();
  const { pushToast } = useFeedback();
  const [step, setStep] = useState<Step>(1);
  const {
    error,
    setError,
    busy,
    setBusy,
    mobileSidebarOpen,
    setMobileSidebarOpen,
    commandPaletteOpen,
    setCommandPaletteOpen,
    keyboardHelpOpen,
    setKeyboardHelpOpen,
    optimisticSaving,
    setOptimisticSaving,
  } = useStudioShellState();

  // Step 1
  const [dsName, setDsName] = useState("");
  const [dsDesc, setDsDesc] = useState("");
  const [datasetId, setDatasetId] = useState("");

  // Step 2
  const [attrs, setAttrs] = useState<AttrRow[]>([newAttr(0)]);
  const [versionId, setVersionId] = useState("");
  const [correlationRulesText, setCorrelationRulesText] = useState("[]");
  const [semanticRulesText, setSemanticRulesText] = useState("[]");
  const [semanticRulesSaving, setSemanticRulesSaving] = useState(false);
  const [semanticRulesDryRunning, setSemanticRulesDryRunning] = useState(false);
  const [semanticRulesInferring, setSemanticRulesInferring] = useState(false);
  const [suggestionsBusy, setSuggestionsBusy] = useState(false);
  const [semanticConflictPolicy, setSemanticConflictPolicy] =
    useState<SemanticConflictPolicy>("priority_wins");
  const [semanticRuleMetadata, setSemanticRuleMetadata] =
    useState<SemanticRulesMetadata | null>(null);
  const [semanticDryRunResult, setSemanticDryRunResult] =
    useState<DryRunSemanticRulesResponse | null>(null);

  // Step 3
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [explainMode, setExplainMode] = useState(false);
  const [explainBusy, setExplainBusy] = useState(false);
  const [selectedExplainCell, setSelectedExplainCell] = useState<{
    rowIndex: number;
    column: string;
  } | null>(null);
  const [selectedExplainTrace, setSelectedExplainTrace] =
    useState<ExplainResponse | null>(null);
  const [compareBusy, setCompareBusy] = useState(false);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(
    null,
  );
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
  const [semanticRuleMetrics, setSemanticRuleMetrics] = useState<Record<
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
  const [streamingBusy, setStreamingBusy] = useState(false);
  const [streamedBytes, setStreamedBytes] = useState(0);
  const [preflightResult, setPreflightResult] =
    useState<GenerationPreflightResponse | null>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [allowLowQualityDownloads, setAllowLowQualityDownloads] =
    useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const { notifyError } = useErrorNotifier(setError);

  const { estimatedCells, useAsyncGeneration, shouldUseAsyncGeneration } =
    resolveGenerationMode(
      rowCount,
      attrs.length,
      AUTO_ASYNC_ROW_THRESHOLD,
      AUTO_ASYNC_CELL_THRESHOLD,
      Boolean(preflightResult?.requires_async),
    );
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

  const {
    correlationRules,
    semanticRules,
    parseCorrelationRules,
    handleCorrelationRulesChange,
    handleSemanticRulesChange,
  } = useStudioRules({
    correlationRulesText,
    semanticRulesText,
    setCorrelationRulesText,
    setSemanticRulesText,
    setSemanticDryRunResult: () => setSemanticDryRunResult(null),
  });
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
            className={`truncate px-4 py-2.5 text-foreground ${
              explainMode
                ? "cursor-pointer hover:bg-primary/10"
                : "cursor-default"
            } ${
              selectedExplainCell?.rowIndex === safeIndex &&
              selectedExplainCell?.column === col
                ? "bg-primary/20"
                : ""
            }`}
            onClick={() => {
              if (!explainMode) return;
              void handleExplainCellClick(safeIndex, col);
            }}
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
        const semanticRulesFromVersion = latest.config_json.semantic_rules;
        if (Array.isArray(correlations)) {
          setCorrelationRulesText(JSON.stringify(correlations, null, 2));
        }
        if (Array.isArray(semanticRulesFromVersion)) {
          setSemanticRulesText(
            JSON.stringify(semanticRulesFromVersion, null, 2),
          );
        }
        if (realism?.metadata) {
          setRealismMetadata(realism.metadata);
        }

        if (latest.id) {
          void (async () => {
            try {
              const semanticResponse = await getSemanticRules(latest.id);
              setSemanticRulesText(
                JSON.stringify(semanticResponse.rules ?? [], null, 2),
              );
              setSemanticRuleMetadata(semanticResponse.metadata ?? null);
              if (semanticResponse.metadata?.conflict_policy) {
                setSemanticConflictPolicy(
                  semanticResponse.metadata.conflict_policy,
                );
              }
            } catch {
              // Ignore if no semantic rules are stored yet.
            }
          })();
        }

        setStep(existingFiles.length > 0 ? 4 : 2);
      })
      .catch(() => setStep(2));
  }, []);

  const handleSuggestSettings = async () => {
    setSuggestionsBusy(true);
    setError("");
    try {
      const response = await suggestDatasetSettings({
        dataset_version_id: versionId || undefined,
        attributes: attrs.map(attrRowToApiAttribute),
      });

      const suggestionMap = new Map<string, AttributeSuggestion>();
      for (const suggestion of response.attribute_suggestions ?? []) {
        suggestionMap.set(suggestion.attribute_name, suggestion);
      }

      setAttrs((prev) =>
        prev.map((attr) => {
          const suggestion = suggestionMap.get(attr.name);
          if (!suggestion) {
            return attr;
          }
          return applySuggestionToAttr(attr, suggestion);
        }),
      );

      const existingRules = parseCorrelationRules();
      const relationshipSuggestions = response.relationship_suggestions ?? [];
      const knownPairs = new Set(
        existingRules.map((rule) => `${rule.source}=>${rule.target}`),
      );
      const mergedRules = [...existingRules];
      for (const suggestion of relationshipSuggestions) {
        const key = `${suggestion.source}=>${suggestion.target}`;
        if (knownPairs.has(key)) {
          continue;
        }
        knownPairs.add(key);
        mergedRules.push({
          source: suggestion.source,
          target: suggestion.target,
          strength: suggestion.strength,
        });
      }
      setCorrelationRulesText(JSON.stringify(mergedRules, null, 2));

      pushToast({
        title: "Suggestions Applied",
        message: `Applied ${response.attribute_suggestions.length} field suggestions and ${relationshipSuggestions.length} relationship hints.`,
        intent: "success",
      });
    } catch (e) {
      notifyError(
        "Suggestions Failed",
        e,
        "Unable to compute suggestions for current field setup.",
      );
    } finally {
      setSuggestionsBusy(false);
    }
  };

  const persistSemanticRules = async (datasetVersionId: string) => {
    setSemanticRulesSaving(true);
    try {
      const response = await upsertSemanticRules(datasetVersionId, {
        rules: semanticRules,
        conflict_policy: semanticConflictPolicy,
      });
      setSemanticRulesText(JSON.stringify(response.rules ?? [], null, 2));
      setSemanticRuleMetadata(response.metadata ?? null);
      if (response.metadata?.conflict_policy) {
        setSemanticConflictPolicy(response.metadata.conflict_policy);
      }
      return response;
    } finally {
      setSemanticRulesSaving(false);
    }
  };

  const handleSaveSemanticRules = async () => {
    if (!versionId) {
      setError(
        "Save attributes first to create a version before saving rules.",
      );
      return;
    }

    setError("");
    try {
      await persistSemanticRules(versionId);
      pushToast({
        title: "Semantic Rules Saved",
        message: "Rules have been saved for the current dataset version.",
        intent: "success",
      });
    } catch (e) {
      const detail = (e as { detail?: unknown }).detail;
      if (
        detail &&
        typeof detail === "object" &&
        "errors" in detail &&
        Array.isArray((detail as { errors?: unknown[] }).errors)
      ) {
        const detailObj = detail as {
          message?: string;
          errors?: string[];
          warnings?: string[];
        };
        setSemanticRuleMetadata({
          is_valid: false,
          errors: detailObj.errors ?? [],
          warnings: detailObj.warnings ?? [],
          conflict_policy: semanticConflictPolicy,
        });
        setError(detailObj.message ?? "Semantic rule validation failed.");
      } else {
        notifyError(
          "Save Semantic Rules Failed",
          e,
          "Unable to save semantic rules.",
        );
      }
    }
  };

  const handleDryRunSemanticRules = async () => {
    if (!versionId) {
      setError(
        "Save attributes first to create a version before running dry-run.",
      );
      return;
    }

    setSemanticRulesDryRunning(true);
    setError("");
    try {
      const response = await dryRunSemanticRules(versionId, {
        rules: semanticRules,
        conflict_policy: semanticConflictPolicy,
        sample_rows: 10,
        seed: seed.trim() ? Number(seed) : undefined,
      });
      setSemanticDryRunResult(response);
      setSemanticRuleMetadata(response.metadata ?? null);
      pushToast({
        title: "Dry Run Completed",
        message: `Changed ${response.metadata.changed_cells ?? 0} cells across ${response.metadata.changed_rows ?? 0} rows.`,
        intent: "success",
      });
    } catch (e) {
      notifyError(
        "Semantic Dry Run Failed",
        e,
        "Unable to run semantic rule dry-run.",
      );
    } finally {
      setSemanticRulesDryRunning(false);
    }
  };

  const handleInferSemanticRules = async () => {
    if (!versionId) {
      setError(
        "Save attributes first to create a version before inferring rules.",
      );
      return;
    }

    setSemanticRulesInferring(true);
    setError("");
    try {
      const response = await inferSemanticRules({
        dataset_version_id: versionId,
        sample_rows: 50,
        max_rules: 20,
        min_confidence: 0.7,
        seed: seed.trim() ? Number(seed) : undefined,
        conflict_policy: semanticConflictPolicy,
      });

      const inferred = response.rules ?? [];
      const nextRules = mergeSemanticRuleSets(semanticRules, inferred);
      setSemanticRulesText(JSON.stringify(nextRules, null, 2));
      setSemanticRuleMetadata(response.metadata ?? null);
      setSemanticDryRunResult(null);

      const addedCount = Math.max(0, nextRules.length - semanticRules.length);
      pushToast({
        title: "Inference Completed",
        message:
          inferred.length === 0
            ? "No new semantic rules were inferred from sampled rows."
            : `Added ${addedCount} inferred rule${addedCount === 1 ? "" : "s"} (${inferred.length} returned).`,
        intent: inferred.length === 0 ? "info" : "success",
      });
    } catch (e) {
      notifyError(
        "Semantic Inference Failed",
        e,
        "Unable to infer semantic rules from current dataset version.",
      );
    } finally {
      setSemanticRulesInferring(false);
    }
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
            attributes: nextAttrs.map(attrRowToApiAttribute),
            seed: seed.trim() ? Number(seed) : undefined,
            correlations,
          });

          if (optimisticSaveSeq.current !== seq) {
            return;
          }

          await persistSemanticRules(res.version_id);

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
    const weightError = attrs
      .map(validateCategoricalWeights)
      .find((value): value is string => Boolean(value));
    if (weightError) {
      setBusy(false);
      setError(weightError);
      return;
    }
    try {
      const correlations = parseCorrelationRules();
      const res = await saveAttributes({
        dataset_id: datasetId,
        attributes: attrs.map(attrRowToApiAttribute),
        seed: seed.trim() ? Number(seed) : undefined,
        correlations,
      });
      await persistSemanticRules(res.version_id);
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
      setSelectedExplainCell(null);
      setSelectedExplainTrace(null);
      setCompareResult(null);

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

  const handleExplainCellClick = async (rowIndex: number, column: string) => {
    if (!versionId) {
      setError("No saved version available for explanations.");
      return;
    }
    setExplainBusy(true);
    setSelectedExplainCell({ rowIndex, column });
    setError("");
    try {
      const response = await explainDatasetRow({
        dataset_version_id: versionId,
        row_index: rowIndex,
        seed: seed.trim() ? Number(seed) : undefined,
        column,
      });
      setSelectedExplainTrace(response);
    } catch (e) {
      notifyError("Explain Failed", e, "Unable to explain selected cell.");
    } finally {
      setExplainBusy(false);
    }
  };

  const handleCompareDrift = async () => {
    if (!versionId) {
      setError("Save attributes first before comparing drift.");
      return;
    }
    if (previewRows.length === 0) {
      setError("Generate preview rows before running comparison.");
      return;
    }

    setCompareBusy(true);
    setError("");
    try {
      const result = await compareDatasetOutput({
        dataset_version_id: versionId,
        generated_data: previewRows,
        seed: seed.trim() ? Number(seed) : undefined,
        sample_rows: previewRows.length,
      });
      setCompareResult(result);
      pushToast({
        title: "Comparison Completed",
        message: `Overall drift score: ${result.overall_drift_score.toFixed(3)}`,
        intent: "success",
      });
    } catch (e) {
      notifyError(
        "Comparison Failed",
        e,
        "Unable to compare generated rows against expected distribution.",
      );
    } finally {
      setCompareBusy(false);
    }
  };

  const handleApplyRefinementRecommendations = () => {
    if (!compareResult || compareResult.recommendations.length === 0) {
      setError("No refinement recommendations available to apply.");
      return;
    }

    const recommendationMap = new Map(
      compareResult.recommendations.map((item) => [item.attribute_name, item]),
    );

    setAttrs((prev) =>
      prev.map((attr) => {
        const recommendation = recommendationMap.get(attr.name);
        if (!recommendation) {
          return attr;
        }
        return {
          ...attr,
          distribution: recommendation.suggested_distribution,
          skew_direction:
            recommendation.suggested_distribution === "skewed"
              ? "right"
              : attr.skew_direction,
        };
      }),
    );

    pushToast({
      title: "Refinement Applied",
      message: `Applied ${compareResult.recommendations.length} recommendation(s). Regenerate preview to evaluate impact.`,
      intent: "success",
    });
  };

  const {
    handleGenerate,
    handleCancelJob,
    handleDownload,
    handleStreamCsvDownload,
    handleSubmitFeedback,
  } = useStudioGenerationFlow({
    datasetId,
    versionId,
    attrs,
    formats,
    rowCount,
    seed,
    shouldUseAsyncGeneration,
    feedbackRating,
    feedbackComment,
    generationSignature,
    jobId,
    setError,
    setBusy,
    setStreamingBusy,
    setStreamedBytes,
    setFeedbackBusy,
    setFeedbackComment,
    setAllowLowQualityDownloads,
    setGeneratedFiles,
    setQualityReport,
    setQualityDashboard,
    setValidationSummary,
    setQualityGuardrails,
    setSemanticRuleMetrics,
    setGenerationSignature,
    setGenerationRunId,
    setRunComparison,
    setJobId,
    setJobStatus,
    setJobStage,
    setJobProgress,
    notifyError,
    pushToast,
    asyncPollIntervalMs: ASYNC_POLL_INTERVAL_MS,
    asyncPollMaxAttempts: ASYNC_POLL_MAX_ATTEMPTS,
  });

  // ── Step 4: Generate ─────────────────────────────────────────

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
          <StudioErrorAlert error={error} onDismiss={() => setError("")} />

          {/* ════════════════ STEP 1 ════════════════ */}
          {step === 1 && (
            <Step1CreateDataset
              dsName={dsName}
              dsDesc={dsDesc}
              busy={busy}
              onNameChange={setDsName}
              onDescriptionChange={setDsDesc}
              onCreate={() => void handleCreate()}
            />
          )}

          {/* ════════════════ STEP 2 ════════════════ */}
          {step === 2 && (
            <Step2DefineFields
              attrs={attrs}
              busy={busy}
              suggestionsBusy={suggestionsBusy}
              versionId={versionId}
              correlationRules={correlationRules}
              semanticRules={semanticRules}
              semanticConflictPolicy={semanticConflictPolicy}
              semanticRuleMetadata={semanticRuleMetadata}
              semanticDryRunResult={semanticDryRunResult}
              semanticRulesSaving={semanticRulesSaving}
              semanticRulesDryRunning={semanticRulesDryRunning}
              semanticRulesInferring={semanticRulesInferring}
              correlationRulesText={correlationRulesText}
              onSuggestSettings={handleSuggestSettings}
              onSaveAndPreview={handleSaveAndPreview}
              onSetStep={setStep}
              onCorrelationRulesChange={handleCorrelationRulesChange}
              onSemanticRulesChange={handleSemanticRulesChange}
              onSemanticConflictPolicyChange={setSemanticConflictPolicy}
              onSaveSemanticRules={handleSaveSemanticRules}
              onDryRunSemanticRules={handleDryRunSemanticRules}
              onInferSemanticRules={handleInferSemanticRules}
              onCorrelationRulesTextChange={setCorrelationRulesText}
              onAddAttr={addAttr}
              onUpdateAttr={updateAttr}
              onRemoveAttr={removeAttr}
            />
          )}

          {/* ════════════════ STEP 3 ════════════════ */}
          {step === 3 && (
            <Step3PreviewRefine
              optimisticSaving={optimisticSaving}
              isRefreshing={isRefreshing}
              compareBusy={compareBusy}
              compareResult={compareResult}
              previewRows={previewRows}
              explainMode={explainMode}
              explainBusy={explainBusy}
              selectedExplainCell={selectedExplainCell}
              selectedExplainTrace={selectedExplainTrace}
              realismMetadata={realismMetadata}
              previewComparisonCols={previewComparisonCols}
              selectedPreviewComparison={selectedPreviewComparison}
              selectedNumericComparison={selectedNumericComparison}
              selectedComparisonCol={selectedComparisonCol}
              previewCols={previewCols}
              previewColumnTemplate={previewColumnTemplate}
              previewRowHeight={PREVIEW_ROW_HEIGHT}
              attrs={attrs}
              onSetStep={setStep}
              onRegenerate={handleRegenerate}
              onCompareDrift={handleCompareDrift}
              onApplyRefinementRecommendations={
                handleApplyRefinementRecommendations
              }
              onSetSelectedComparisonCol={setSelectedComparisonCol}
              onToggleExplainMode={() => {
                setExplainMode((prev) => !prev);
                setSelectedExplainCell(null);
                setSelectedExplainTrace(null);
              }}
              onExplainCellClick={handleExplainCellClick}
              renderPreviewRow={renderPreviewRow}
              onUpdateAttr={updateAttr}
            />
          )}

          {/* ════════════════ STEP 4 ════════════════ */}
          {step === 4 && (
            <Step4Generate
              generatedFiles={generatedFiles}
              rowCount={rowCount}
              formats={formats}
              seed={seed}
              attrsCount={attrs.length}
              busy={busy}
              streamingBusy={streamingBusy}
              streamedBytes={streamedBytes}
              versionId={versionId}
              shouldUseAsyncGeneration={shouldUseAsyncGeneration}
              preflightBusy={preflightBusy}
              preflightResult={preflightResult}
              jobId={jobId}
              jobStatus={jobStatus}
              jobStage={jobStage}
              jobProgress={jobProgress}
              driftEnabled={driftEnabled}
              driftIntensity={driftIntensity}
              driftColumnsText={driftColumnsText}
              guardrailsPassed={guardrailsPassed}
              allowLowQualityDownloads={allowLowQualityDownloads}
              feedbackRating={feedbackRating}
              feedbackComment={feedbackComment}
              feedbackBusy={feedbackBusy}
              qualityDashboard={qualityDashboard}
              validationSummary={validationSummary}
              qualityReport={qualityReport}
              qualityGuardrails={qualityGuardrails}
              semanticRuleMetrics={semanticRuleMetrics}
              runComparison={runComparison}
              generationRunId={generationRunId}
              generationSignature={generationSignature}
              autoAsyncRowThreshold={AUTO_ASYNC_ROW_THRESHOLD}
              autoAsyncCellThreshold={AUTO_ASYNC_CELL_THRESHOLD}
              onSetStep={setStep}
              onSetRowCount={setRowCount}
              onToggleFormat={toggleFormat}
              onSetSeed={setSeed}
              onGenerate={handleGenerate}
              onStreamCsvDownload={handleStreamCsvDownload}
              onCancelJob={handleCancelJob}
              onSetDriftEnabled={setDriftEnabled}
              onSetDriftIntensity={setDriftIntensity}
              onSetDriftColumnsText={setDriftColumnsText}
              onDownload={handleDownload}
              onSetAllowLowQualityDownloads={setAllowLowQualityDownloads}
              onFeedbackRatingSelect={setFeedbackRating}
              onFeedbackCommentChange={setFeedbackComment}
              onSubmitFeedback={handleSubmitFeedback}
              onGenerateAgain={() => {
                setGeneratedFiles([]);
                setQualityReport(null);
                setQualityDashboard(null);
                setQualityGuardrails(null);
                setValidationSummary(null);
                setSemanticRuleMetrics(null);
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
            />
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
