import { Card } from "@/components/ui/card";
import type { ExplainResponse } from "@/lib/api-client";

interface CellExplanationCardProps {
  explainBusy: boolean;
  selectedExplainCell: { rowIndex: number; column: string } | null;
  selectedExplainTrace: ExplainResponse | null;
}

export function CellExplanationCard({
  explainBusy,
  selectedExplainCell,
  selectedExplainTrace,
}: CellExplanationCardProps) {
  return (
    <Card className="border-border bg-card/70 p-4">
      <p className="text-sm font-semibold text-foreground">Cell Explanation</p>
      {explainBusy ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Fetching explanation...
        </p>
      ) : selectedExplainCell && selectedExplainTrace ? (
        <div className="mt-3 space-y-2 text-xs text-muted-foreground">
          <p>
            Row {selectedExplainCell.rowIndex + 1} · Column{" "}
            {selectedExplainCell.column}
          </p>
          <p>
            Value:{" "}
            {String(
              selectedExplainTrace.row[selectedExplainCell.column] ?? "null",
            )}
          </p>
          <p>
            Source:{" "}
            {selectedExplainTrace.trace[selectedExplainCell.column]?.source ??
              "unknown"}
          </p>
          <p>
            Generator:{" "}
            {selectedExplainTrace.trace[selectedExplainCell.column]
              ?.generator ?? "n/a"}
          </p>
          <p>
            Rule:{" "}
            {selectedExplainTrace.trace[selectedExplainCell.column]?.rule ??
              "none"}
          </p>
          <p>
            Depends On:{" "}
            {(
              selectedExplainTrace.trace[selectedExplainCell.column]
                ?.depends_on ?? []
            ).join(", ") || "none"}
          </p>
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          Click any cell to see why its value was generated.
        </p>
      )}
    </Card>
  );
}
