import { CellExplanationCard } from "@/components/studio/cell-explanation-card";
import { Step3PreviewContent } from "@/components/studio/steps/step-3-preview-content";
import { Step3HeaderActions } from "@/components/studio/steps/step-3-header-actions";
import { Step3QuickAdjustments } from "@/components/studio/steps/step-3-quick-adjustments";
import { Step3RealismCard } from "@/components/studio/steps/step-3-realism-card";
import type { AttrRow, AttrUpdate, Step } from "@/components/studio/types";
import type {
  CompareResponse,
  ExplainResponse,
  PreviewColumnComparison,
} from "@/lib/api-client";

export interface Step3PreviewRefineProps {
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
      <Step3HeaderActions
        optimisticSaving={optimisticSaving}
        isRefreshing={isRefreshing}
        compareBusy={compareBusy}
        compareResult={compareResult}
        previewRowsCount={previewRows.length}
        onSetStep={onSetStep as (step: 2 | 4) => void}
        onRegenerate={onRegenerate}
        onCompareDrift={onCompareDrift}
        onApplyRefinementRecommendations={onApplyRefinementRecommendations}
      />

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

      <Step3PreviewContent
        isRefreshing={isRefreshing}
        compareResult={compareResult}
        previewComparisonCols={previewComparisonCols}
        selectedPreviewComparison={selectedPreviewComparison}
        selectedNumericComparison={selectedNumericComparison}
        selectedComparisonCol={selectedComparisonCol}
        previewRows={previewRows}
        previewCols={previewCols}
        previewColumnTemplate={previewColumnTemplate}
        previewRowHeight={previewRowHeight}
        explainMode={explainMode}
        onSetSelectedComparisonCol={onSetSelectedComparisonCol}
        onToggleExplainMode={onToggleExplainMode}
        onExplainCellClick={onExplainCellClick}
        renderPreviewRow={renderPreviewRow}
      />

      <Step3QuickAdjustments
        attrs={attrs}
        isRefreshing={isRefreshing}
        onRegenerate={onRegenerate}
        onUpdateAttr={onUpdateAttr}
      />
    </div>
  );
}
