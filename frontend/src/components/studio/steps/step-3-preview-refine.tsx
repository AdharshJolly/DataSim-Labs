import { LoaderCircle } from "lucide-react";

import { CellExplanationCard } from "@/components/studio/cell-explanation-card";
import { QuickAdjustCard } from "@/components/studio/quick-adjust-card";
import { RefinementCard } from "@/components/studio/refinement-card";
import { Step3ComparisonCard } from "@/components/studio/steps/step-3-comparison-card";
import { Step3PreviewPanel } from "@/components/studio/steps/step-3-preview-panel";
import { Step3RealismCard } from "@/components/studio/steps/step-3-realism-card";
import type { AttrRow, AttrUpdate, Step } from "@/components/studio/types";
import { Button } from "@/components/ui/button";
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
        <Step3RealismCard realismMetadata={realismMetadata} />
      )}

      <Step3ComparisonCard
        previewComparisonCols={previewComparisonCols}
        selectedPreviewComparison={selectedPreviewComparison}
        selectedNumericComparison={selectedNumericComparison}
        selectedComparisonCol={selectedComparisonCol}
        onSetSelectedComparisonCol={onSetSelectedComparisonCol}
      />

      {compareResult && <RefinementCard compareResult={compareResult} />}

      {isRefreshing ? (
        <div className="flex h-60 flex-col items-center justify-center gap-3 rounded-lg border border-border bg-background/70">
          <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">
            Generating sample…
          </span>
        </div>
      ) : (
        <Step3PreviewPanel
          previewRows={previewRows}
          previewCols={previewCols}
          previewColumnTemplate={previewColumnTemplate}
          previewRowHeight={previewRowHeight}
          explainMode={explainMode}
          onToggleExplainMode={onToggleExplainMode}
          onExplainCellClick={onExplainCellClick}
          renderPreviewRow={renderPreviewRow}
        />
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
