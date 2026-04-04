import { LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { CompareResponse } from "@/lib/api-client";

interface Step3HeaderActionsProps {
  optimisticSaving: boolean;
  isRefreshing: boolean;
  compareBusy: boolean;
  compareResult: CompareResponse | null;
  previewRowsCount: number;
  onSetStep: (step: 2 | 4) => void;
  onRegenerate: () => Promise<void>;
  onCompareDrift: () => Promise<void>;
  onApplyRefinementRecommendations: () => void;
}

export function Step3HeaderActions({
  optimisticSaving,
  isRefreshing,
  compareBusy,
  compareResult,
  previewRowsCount,
  onSetStep,
  onRegenerate,
  onCompareDrift,
  onApplyRefinementRecommendations,
}: Step3HeaderActionsProps) {
  return (
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
          disabled={compareBusy || previewRowsCount === 0}
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
  );
}
