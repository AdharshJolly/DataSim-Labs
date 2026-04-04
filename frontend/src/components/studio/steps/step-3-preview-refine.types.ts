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
