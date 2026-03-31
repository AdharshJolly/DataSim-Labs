import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  LoaderCircle,
} from "lucide-react";

import { FeedbackLearningCard } from "@/components/studio/feedback-learning-card";
import { FORMAT_OPTIONS } from "@/components/studio/constants";
import { formatBytes } from "@/components/studio/helpers";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { ValidationDashboard } from "@/components/studio/validation-dashboard";
import type { Step } from "@/components/studio/types";
import type { GeneratedFileInfo } from "@/lib/api-client";

interface Step4GenerateProps {
  generatedFiles: GeneratedFileInfo[];
  rowCount: number;
  formats: Array<"csv" | "json" | "jsonl" | "excel">;
  seed: string;
  attrsCount: number;
  busy: boolean;
  streamingBusy: boolean;
  streamedBytes: number;
  versionId: string;
  shouldUseAsyncGeneration: boolean;
  preflightBusy: boolean;
  preflightResult: {
    issues?: Array<{ code: string; message: string }>;
  } | null;
  jobId: string;
  jobStatus: string;
  jobStage: string;
  jobProgress: number;
  driftEnabled: boolean;
  driftIntensity: number;
  driftColumnsText: string;
  guardrailsPassed: boolean;
  allowLowQualityDownloads: boolean;
  feedbackRating: number;
  feedbackComment: string;
  feedbackBusy: boolean;
  qualityDashboard: {
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
  } | null;
  validationSummary: any;
  qualityReport: Record<string, unknown> | null;
  qualityGuardrails: Record<string, unknown> | null;
  semanticRuleMetrics: Record<string, unknown> | null;
  runComparison: Record<string, unknown> | null;
  generationRunId: string;
  generationSignature: string;
  autoAsyncRowThreshold: number;
  autoAsyncCellThreshold: number;
  onSetStep: (step: Step) => void;
  onSetRowCount: (value: number) => void;
  onToggleFormat: (format: "csv" | "json" | "jsonl" | "excel") => void;
  onSetSeed: (value: string) => void;
  onGenerate: () => Promise<void>;
  onStreamCsvDownload: () => Promise<void>;
  onCancelJob: () => Promise<void>;
  onSetDriftEnabled: (enabled: boolean) => void;
  onSetDriftIntensity: (value: number) => void;
  onSetDriftColumnsText: (value: string) => void;
  onDownload: (format: string) => Promise<void>;
  onSetAllowLowQualityDownloads: (enabled: boolean) => void;
  onFeedbackRatingSelect: (rating: number) => void;
  onFeedbackCommentChange: (value: string) => void;
  onSubmitFeedback: () => Promise<void>;
  onGenerateAgain: () => void;
}

export function Step4Generate({
  generatedFiles,
  rowCount,
  formats,
  seed,
  attrsCount,
  busy,
  streamingBusy,
  streamedBytes,
  versionId,
  shouldUseAsyncGeneration,
  preflightBusy,
  preflightResult,
  jobId,
  jobStatus,
  jobStage,
  jobProgress,
  driftEnabled,
  driftIntensity,
  driftColumnsText,
  guardrailsPassed,
  allowLowQualityDownloads,
  feedbackRating,
  feedbackComment,
  feedbackBusy,
  qualityDashboard,
  validationSummary,
  qualityReport,
  qualityGuardrails,
  semanticRuleMetrics,
  runComparison,
  generationRunId,
  generationSignature,
  autoAsyncRowThreshold,
  autoAsyncCellThreshold,
  onSetStep,
  onSetRowCount,
  onToggleFormat,
  onSetSeed,
  onGenerate,
  onStreamCsvDownload,
  onCancelJob,
  onSetDriftEnabled,
  onSetDriftIntensity,
  onSetDriftColumnsText,
  onDownload,
  onSetAllowLowQualityDownloads,
  onFeedbackRatingSelect,
  onFeedbackCommentChange,
  onSubmitFeedback,
  onGenerateAgain,
}: Step4GenerateProps) {
  return (
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
                  onChange={(e) => onSetRowCount(Number(e.target.value))}
                  className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                />
                <input
                  type="number"
                  min={1}
                  max={10000000}
                  className="w-32 text-center font-semibold"
                  value={rowCount}
                  onChange={(e) =>
                    onSetRowCount(Math.max(1, Number(e.target.value) || 1))
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">
                Output Format
              </label>
              <div className="mt-1 flex flex-wrap gap-3">
                {FORMAT_OPTIONS.map(({ value, label, icon: Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => onToggleFormat(value)}
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
                onChange={(e) => onSetSeed(e.target.value)}
              />
              <p className="pt-1 text-xs text-muted-foreground/70">
                Use the same seed to regenerate identical datasets.
              </p>
            </div>

            <div className="space-y-3 rounded-lg border border-border bg-card/70 p-4">
              <p className="text-sm font-medium text-foreground">
                Generation mode:{" "}
                {shouldUseAsyncGeneration ? "Background job" : "Immediate"}
              </p>
              <p className="text-xs text-muted-foreground">
                Auto-selected by thresholds (
                {autoAsyncRowThreshold.toLocaleString()} rows or{" "}
                {autoAsyncCellThreshold.toLocaleString()} estimated cells).
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
                        <p className="mt-1">No blocking risks detected.</p>
                      )}
                    </>
                  )}
                </div>
              )}

              {jobId && (
                <div className="space-y-2 text-xs text-muted-foreground">
                  <div>
                    <span className="text-foreground">Job ID:</span> {jobId}
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
                  onChange={(e) => onSetDriftEnabled(e.target.checked)}
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
                        onSetDriftIntensity(Number(e.target.value))
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
                      onChange={(e) => onSetDriftColumnsText(e.target.value)}
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => onSetStep(3)}
              >
                ← Back to Preview
              </Button>
              <Button
                type="button"
                variant="default"
                disabled={busy || formats.length === 0}
                onClick={() => void onGenerate()}
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
              <Button
                type="button"
                variant="outline"
                disabled={streamingBusy || !versionId}
                onClick={() => void onStreamCsvDownload()}
              >
                {streamingBusy
                  ? `Streaming... ${formatBytes(streamedBytes)}`
                  : "Live Stream CSV"}
              </Button>
              {shouldUseAsyncGeneration && jobId && busy && (
                <Button
                  type="button"
                  variant="outline"
                  className="border-amber-400/50 text-amber-200 hover:bg-amber-500/10 hover:text-amber-100"
                  onClick={() => void onCancelJob()}
                >
                  Cancel Job
                </Button>
              )}
            </div>
          </div>
        </>
      ) : (
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
                {rowCount.toLocaleString()} rows · {attrsCount} columns ·{" "}
                {generatedFiles.length}{" "}
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
                  disabled={!guardrailsPassed && !allowLowQualityDownloads}
                  onClick={() => void onDownload(file.format)}
                >
                  <Download className="mr-1.5 h-3 w-3" />
                  Download
                </Button>
              </div>
            ))}
          </div>

          <FeedbackLearningCard
            feedbackRating={feedbackRating}
            feedbackComment={feedbackComment}
            feedbackBusy={feedbackBusy}
            onRatingSelect={onFeedbackRatingSelect}
            onCommentChange={onFeedbackCommentChange}
            onSubmit={() => void onSubmitFeedback()}
          />

          {!guardrailsPassed && (
            <Alert>
              <AlertTriangle className="h-5 w-5" />
              <AlertDescription className="space-y-2">
                <p>
                  Quality guardrails reported warnings above threshold. Review
                  diagnostics before downloading.
                </p>
                <label className="inline-flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={allowLowQualityDownloads}
                    onChange={(e) =>
                      onSetAllowLowQualityDownloads(e.target.checked)
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
                    <span className="text-lg text-muted-foreground">/100</span>
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
                        {qualityDashboard.warnings.map((warning, index) => (
                          <li key={`warn-${index}`}>- {warning}</li>
                        ))}
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
                            <li key={`rec-${index}`}>- {recommendation}</li>
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
                <span className="text-foreground">Semantic applied rows:</span>{" "}
                {String(
                  ((
                    semanticRuleMetrics?.totals as
                      | Record<string, unknown>
                      | undefined
                  )?.applied_rows as number | undefined) ?? 0,
                )}
              </div>
              <div>
                <span className="text-foreground">Guardrails:</span>{" "}
                {qualityGuardrails
                  ? String(qualityGuardrails.passed ? "passed" : "failed")
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
                  Alerts: {String(qualityGuardrails.actual_alerts ?? 0)} /{" "}
                  {String(qualityGuardrails.max_alerts ?? 0)}
                </p>
              </div>
            )}

            <div className="mt-3 rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">Drift Simulation</p>
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
                  )?.rule_impacts as Record<string, number> | undefined) ?? {},
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

            {semanticRuleMetrics && (
              <div className="mt-3 rounded border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
                <p className="font-medium text-foreground">
                  Semantic Rule Metrics
                </p>
                <div className="mt-2 space-y-1">
                  {Object.entries(
                    (semanticRuleMetrics.rule_metrics as
                      | Record<string, Record<string, unknown>>
                      | undefined) ?? {},
                  ).map(([ruleId, metric]) => (
                    <p key={ruleId}>
                      {ruleId}: applied {String(metric.applied_rows ?? 0)},
                      skipped {String(metric.skipped_rows ?? 0)}, errors{" "}
                      {String(metric.error_rows ?? 0)}
                    </p>
                  ))}
                </div>
              </div>
            )}

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
            <Button type="button" variant="outline" onClick={onGenerateAgain}>
              Generate Again
            </Button>
            <Button asChild variant="default">
              <Link href="/dashboard">Back to Dashboard</Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
