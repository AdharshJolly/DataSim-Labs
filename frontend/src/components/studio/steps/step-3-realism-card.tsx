import { Card } from "@/components/ui/card";

interface Step3RealismCardProps {
  realismMetadata: Record<string, unknown>;
}

export function Step3RealismCard({ realismMetadata }: Step3RealismCardProps) {
  return (
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
            <p className="font-medium text-foreground">Rule explainability</p>
            <p className="mt-1">
              {realismMetadata.rule_explanations.length} rule explanations
              available in version metadata.
            </p>
          </div>
        )}
    </Card>
  );
}
