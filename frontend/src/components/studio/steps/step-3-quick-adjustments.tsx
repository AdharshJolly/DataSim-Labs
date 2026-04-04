import { QuickAdjustCard } from "@/components/studio/quick-adjust-card";
import type { AttrRow, AttrUpdate } from "@/components/studio/types";
import { Button } from "@/components/ui/button";

interface Step3QuickAdjustmentsProps {
  attrs: AttrRow[];
  isRefreshing: boolean;
  onRegenerate: () => Promise<void>;
  onUpdateAttr: AttrUpdate;
}

export function Step3QuickAdjustments({
  attrs,
  isRefreshing,
  onRegenerate,
  onUpdateAttr,
}: Step3QuickAdjustmentsProps) {
  return (
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
  );
}
