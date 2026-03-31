import Link from "next/link";
import { AlertTriangle, CheckCircle2, Download } from "lucide-react";

import { FeedbackLearningCard } from "@/components/studio/feedback-learning-card";
import { ValidationDashboard } from "@/components/studio/validation-dashboard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { GeneratedFileInfo } from "@/lib/api-client";

interface Step4ResultsPanelProps {
  generatedFiles: GeneratedFileInfo[];
  rowCount: number;
  attrsCount: number;
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
  driftEnabled: boolean;
  driftIntensity: number;
  formatBytes: (bytes: number) => string;
  onDownload: (format: string) => Promise<void>;
  onSetAllowLowQualityDownloads: (enabled: boolean) => void;
  onFeedbackRatingSelect: (rating: number) => void;
  onFeedbackCommentChange: (value: string) => void;
  onSubmitFeedback: () => Promise<void>;
  onGenerateAgain: () => void;
}

export function Step4ResultsPanel({
  generatedFiles,
  rowCount,
  attrsCount,
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
  driftEnabled,
  driftIntensity,
  formatBytes,
  onDownload,
  onSetAllowLowQualityDownloads,
  onFeedbackRatingSelect,
  onFeedbackCommentChange,
  onSubmitFeedback,
  onGenerateAgain,
}: Step4ResultsPanelProps) {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full bg-green-500/10 text-3xl text-green-400">
          <CheckCircle2 className="h-10 w-10" />
        </div>
        <div>
          <h2 className="font-display text-3xl font-bold">Dataset Ready!</h2>
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

      {validationSummary && <ValidationDashboard report={validationSummary} />}

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
            <span className="text-foreground">Rows affected by realism:</span>{" "}
            {String(
              ((qualityReport?.realism as Record<string, unknown> | undefined)
                ?.total_rows_affected as number | undefined) ?? 0,
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
            <p className="font-medium text-foreground">Quality Guardrails</p>
            <p className="mt-1">{String(qualityGuardrails.message ?? "")}</p>
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
          <p className="text-xs font-medium text-foreground">Rule Impacts</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {Object.entries(
              ((qualityReport?.realism as Record<string, unknown> | undefined)
                ?.rule_impacts as Record<string, number> | undefined) ?? {},
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
            <p className="font-medium text-foreground">Semantic Rule Metrics</p>
            <div className="mt-2 space-y-1">
              {Object.entries(
                (semanticRuleMetrics.rule_metrics as
                  | Record<string, Record<string, unknown>>
                  | undefined) ?? {},
              ).map(([ruleId, metric]) => (
                <p key={ruleId}>
                  {ruleId}: applied {String(metric.applied_rows ?? 0)}, skipped{" "}
                  {String(metric.skipped_rows ?? 0)}, errors{" "}
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
              Previous run id: {String(runComparison.previous_run_id ?? "n/a")}
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
  );
}
