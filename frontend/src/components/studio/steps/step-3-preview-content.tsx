import { LoaderCircle } from "lucide-react";

import { RefinementCard } from "@/components/studio/refinement-card";
import { Step3ComparisonCard } from "@/components/studio/steps/step-3-comparison-card";
import { Step3PreviewPanel } from "@/components/studio/steps/step-3-preview-panel";
import type {
  CompareResponse,
  PreviewColumnComparison,
} from "@/lib/api-client";

interface Step3PreviewContentProps {
  isRefreshing: boolean;
  compareResult: CompareResponse | null;
  previewComparisonCols: PreviewColumnComparison[];
  selectedPreviewComparison: PreviewColumnComparison | null;
  selectedNumericComparison: PreviewColumnComparison["numeric"] | null;
  selectedComparisonCol: string;
  previewRows: Record<string, unknown>[];
  previewCols: string[];
  previewColumnTemplate: string;
  previewRowHeight: number;
  explainMode: boolean;
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
}

export function Step3PreviewContent({
  isRefreshing,
  compareResult,
  previewComparisonCols,
  selectedPreviewComparison,
  selectedNumericComparison,
  selectedComparisonCol,
  previewRows,
  previewCols,
  previewColumnTemplate,
  previewRowHeight,
  explainMode,
  onSetSelectedComparisonCol,
  onToggleExplainMode,
  onExplainCellClick,
  renderPreviewRow,
}: Step3PreviewContentProps) {
  return (
    <>
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
    </>
  );
}
