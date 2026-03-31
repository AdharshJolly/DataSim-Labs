import { Card } from "@/components/ui/card";
import type { PreviewColumnComparison } from "@/lib/api-client";

interface Step3ComparisonCardProps {
  previewComparisonCols: PreviewColumnComparison[];
  selectedPreviewComparison: PreviewColumnComparison | null;
  selectedNumericComparison: PreviewColumnComparison["numeric"] | null;
  selectedComparisonCol: string;
  onSetSelectedComparisonCol: (column: string) => void;
}

export function Step3ComparisonCard({
  previewComparisonCols,
  selectedPreviewComparison,
  selectedNumericComparison,
  selectedComparisonCol,
  onSetSelectedComparisonCol,
}: Step3ComparisonCardProps) {
  if (previewComparisonCols.length === 0) {
    return null;
  }

  return (
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
                <span className="text-muted-foreground">Expected range:</span>{" "}
                {selectedNumericComparison.expected_min?.toFixed(2) ?? "n/a"} -{" "}
                {selectedNumericComparison.expected_max?.toFixed(2) ?? "n/a"}
              </div>
              <div>
                <span className="text-muted-foreground">Synthetic range:</span>{" "}
                {selectedNumericComparison.synthetic_min?.toFixed(2) ?? "n/a"} -{" "}
                {selectedNumericComparison.synthetic_max?.toFixed(2) ?? "n/a"}
              </div>
              <div>
                <span className="text-muted-foreground">Expected mean:</span>{" "}
                {selectedNumericComparison.expected_mean?.toFixed(3) ?? "n/a"}
              </div>
              <div>
                <span className="text-muted-foreground">Synthetic mean:</span>{" "}
                {selectedNumericComparison.synthetic_mean?.toFixed(3) ?? "n/a"}
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
                        Math.max(entry.expected_count, entry.synthetic_count),
                      ),
                    );
                    const expectedWidth = (bin.expected_count / maxCount) * 100;
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
  );
}
