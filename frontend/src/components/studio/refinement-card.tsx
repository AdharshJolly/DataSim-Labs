import { Card } from "@/components/ui/card";
import type { CompareResponse } from "@/lib/api-client";

interface RefinementCardProps {
  compareResult: CompareResponse;
}

export function RefinementCard({ compareResult }: RefinementCardProps) {
  return (
    <Card className="mb-6 border-border bg-card/70 p-4">
      <p className="text-sm font-semibold text-foreground">
        Iterative Refinement
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Drift score: {compareResult.overall_drift_score.toFixed(3)}
      </p>
      <div className="mt-3 space-y-2 text-xs text-muted-foreground">
        {compareResult.metrics.slice(0, 6).map((metric) => (
          <div
            key={metric.column}
            className="rounded-md border border-border/60 bg-background/60 px-3 py-2"
          >
            <p className="font-medium text-foreground">{metric.column}</p>
            <p>
              mean diff {metric.mean_diff.toFixed(3)} · variance diff{" "}
              {metric.variance_diff.toFixed(3)} · KL{" "}
              {metric.kl_divergence.toFixed(3)}
            </p>
          </div>
        ))}
        {compareResult.recommendations.length > 0 ? (
          <p>
            Recommendations: {compareResult.recommendations.length} (use Improve
            to apply).
          </p>
        ) : (
          <p>No recommendations were generated for this preview.</p>
        )}
      </div>
    </Card>
  );
}
