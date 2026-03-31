import { List } from "react-window";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Step3PreviewPanelProps {
  previewRows: Record<string, unknown>[];
  previewCols: string[];
  previewColumnTemplate: string;
  previewRowHeight: number;
  explainMode: boolean;
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

export function Step3PreviewPanel({
  previewRows,
  previewCols,
  previewColumnTemplate,
  previewRowHeight,
  explainMode,
  onToggleExplainMode,
  onExplainCellClick,
  renderPreviewRow,
}: Step3PreviewPanelProps) {
  if (previewRows.length === 0) {
    return (
      <div className="flex h-60 items-center justify-center rounded-lg border-2 border-dashed border-border/50 text-sm text-muted-foreground">
        No preview data yet - click Regenerate.
      </div>
    );
  }

  return (
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
  );
}
