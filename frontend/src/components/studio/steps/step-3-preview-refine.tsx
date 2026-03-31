import { List } from "react-window";
import { LoaderCircle } from "lucide-react";

import { CellExplanationCard } from "@/components/studio/cell-explanation-card";
import { QuickAdjustCard } from "@/components/studio/quick-adjust-card";
import { RefinementCard } from "@/components/studio/refinement-card";
import type { AttrRow, AttrUpdate, Step } from "@/components/studio/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type {
  CompareResponse,
  ExplainResponse,
  PreviewColumnComparison,
} from "@/lib/api-client";

interface Step3PreviewRefineProps {
  optimisticSaving: boolean;
  isRefreshing: boolean;
  compareBusy: boolean;
  compareResult: CompareResponse | null;
  previewRows: Record<string, unknown>[];
  explainMode: boolean;
  explainBusy: boolean;
  selectedExplainCell: { rowIndex: number; column: string } | null;
  selectedExplainTrace: ExplainResponse | null;
  realismMetadata: Record<string, unknown> | null;
  previewComparisonCols: PreviewColumnComparison[];
  selectedPreviewComparison: PreviewColumnComparison | null;
  selectedNumericComparison: PreviewColumnComparison["numeric"] | null;
  selectedComparisonCol: string;
  previewCols: string[];
  previewColumnTemplate: string;
  previewRowHeight: number;
  attrs: AttrRow[];
  onSetStep: (step: Step) => void;
  onRegenerate: () => Promise<void>;
  onCompareDrift: () => Promise<void>;
  onApplyRefinementRecommendations: () => void;
  onSetSelectedComparisonCol: (column: string) => void;
  onToggleExplainMode: () => void;
  onExplainCellClick: (rowIndex: number, column: string) => Promise<void>;
  renderPreviewRow: ({
    index,
    style,
  }: {
    index?: number;
    style?: React.CSSProperties;
    [key: string]: unknown;
  }) => React.ReactElement;
  onUpdateAttr: AttrUpdate;
}

export function Step3PreviewRefine({
  optimisticSaving,
  isRefreshing,
  compareBusy,
  compareResult,
  previewRows,
  explainMode,
  explainBusy,
  selectedExplainCell,
  selectedExplainTrace,
  realismMetadata,
  previewComparisonCols,
  selectedPreviewComparison,
  selectedNumericComparison,
  selectedComparisonCol,
  previewCols,
  previewColumnTemplate,
  previewRowHeight,
  attrs,
  onSetStep,
  onRegenerate,
  onCompareDrift,
  onApplyRefinementRecommendations,
  onSetSelectedComparisonCol,
  onToggleExplainMode,
  onExplainCellClick,
  renderPreviewRow,
  onUpdateAttr,
}: Step3PreviewRefineProps) {
  return (
    <div>
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold">Preview & Refine</h1>
          <p className="mt-2 text-muted-foreground">
            Review 10 sample rows. Tweak the field settings below and regenerate
            until the data looks right.
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
            onClick={() => onSetStep(2)}
          >
            ← Edit Fields
          </Button>
          <Button
            type="button"
            variant="outline"
            className="min-h-12"
            disabled={isRefreshing}
            onClick={() => void onRegenerate()}
          >
            {isRefreshing ? (
              <span className="flex items-center gap-2">
                <LoaderCircle className="h-4 w-4 animate-spin" /> Regenerating…
              </span>
            ) : (
              "↺ Regenerate"
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="min-h-12"
            disabled={compareBusy || previewRows.length === 0}
            onClick={() => void onCompareDrift()}
          >
            {compareBusy ? "Comparing..." : "Compare Drift"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="min-h-12"
            disabled={
              !compareResult || compareResult.recommendations.length === 0
            }
            onClick={onApplyRefinementRecommendations}
          >
            Improve
          </Button>
          <Button
            type="button"
            variant="default"
            className="min-h-12"
            onClick={() => onSetStep(4)}
          >
            Looks Good →
          </Button>
        </div>
      </header>

      {explainMode && (
        <CellExplanationCard
          explainBusy={explainBusy}
          selectedExplainCell={selectedExplainCell}
          selectedExplainTrace={selectedExplainTrace}
        />
      )}

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
                  {realismMetadata.conflicts.slice(0, 3).map((item, idx) => {
                    const conflict = item as Record<string, unknown>;
                    return (
                      <li key={idx}>
                        {String(conflict.type ?? "conflict")}:{" "}
                        {String(conflict.details ?? "details unavailable")}
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
                  {realismMetadata.rule_explanations.length} rule explanations
                  available in version metadata.
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
              value={selectedPreviewComparison?.column ?? selectedComparisonCol}
              onChange={(e) => onSetSelectedComparisonCol(e.target.value)}
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
                    {selectedNumericComparison.expected_min?.toFixed(2) ??
                      "n/a"}{" "}
                    -{" "}
                    {selectedNumericComparison.expected_max?.toFixed(2) ??
                      "n/a"}
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      Synthetic range:
                    </span>{" "}
                    {selectedNumericComparison.synthetic_min?.toFixed(2) ??
                      "n/a"}{" "}
                    -{" "}
                    {selectedNumericComparison.synthetic_max?.toFixed(2) ??
                      "n/a"}
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      Expected mean:
                    </span>{" "}
                    {selectedNumericComparison.expected_mean?.toFixed(3) ??
                      "n/a"}
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      Synthetic mean:
                    </span>{" "}
                    {selectedNumericComparison.synthetic_mean?.toFixed(3) ??
                      "n/a"}
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-background/60 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Histogram Overlay
                </p>
                <div className="mt-3 space-y-2">
                  {selectedNumericComparison.histogram_bins.length > 0 ? (
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
                          <div key={`${bin.bin_start}-${bin.bin_end}-${index}`}>
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
              Detailed statistical comparison is currently available for numeric
              columns.
            </p>
          )}
        </Card>
      )}

      {compareResult && <RefinementCard compareResult={compareResult} />}

      {isRefreshing ? (
        <div className="flex h-60 flex-col items-center justify-center gap-3 rounded-lg border border-border bg-background/70">
          <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">
            Generating sample…
          </span>
        </div>
      ) : previewRows.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
            <span>
              {previewRows.length.toLocaleString()} rows · {previewCols.length}{" "}
              columns
            </span>
            <Button
              type="button"
              size="sm"
              variant={explainMode ? "default" : "outline"}
              onClick={onToggleExplainMode}
            >
              {explainMode ? "Explain Mode On" : "Explain Mode"}
            </Button>
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
                        <button
                          type="button"
                          className={`w-full truncate text-right ${
                            explainMode
                              ? "cursor-pointer rounded px-1 py-0.5 hover:bg-primary/10"
                              : "cursor-default"
                          }`}
                          onClick={() => {
                            if (!explainMode) return;
                            void onExplainCellClick(index, col);
                          }}
                        >
                          {row[col] == null ? "null" : String(row[col])}
                        </button>
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
                    Math.max(220, previewRows.length * previewRowHeight),
                  ),
                  width: "100%",
                }}
                rowCount={previewRows.length}
                rowHeight={previewRowHeight}
                rowComponent={renderPreviewRow}
                rowProps={{}}
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="flex h-60 items-center justify-center rounded-lg border-2 border-dashed border-border/50 text-sm text-muted-foreground">
          No preview data yet - click Regenerate.
        </div>
      )}

      <div className="mt-12">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-2xl font-bold">Quick Adjustments</h2>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="h-9 px-3 text-xs"
            disabled={isRefreshing}
            onClick={() => void onRegenerate()}
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
              onUpdate={onUpdateAttr}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
