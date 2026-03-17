import { NUMERIC_TYPES } from "./constants";
import { typeLabel } from "./helpers";
import type { AttrRow, AttrUpdate } from "./types";

interface QuickAdjustProps {
  attr: AttrRow;
  index: number;
  onUpdate: AttrUpdate;
}

export function QuickAdjustCard({ attr, index, onUpdate }: QuickAdjustProps) {
  const showMinMax = NUMERIC_TYPES.includes(attr.type);
  const showCats = attr.type === "categorical";

  return (
    <div className="space-y-3 rounded-lg border border-border bg-gradient-to-br from-white/[0.03] to-transparent backdrop-blur-[2px] p-3 transition-all hover:border-primary/30">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-semibold text-foreground">
          {attr.name}
        </span>
        <span className="flex-shrink-0 rounded-full bg-secondary/10 px-2 py-0.5 text-xs font-medium text-secondary">
          {typeLabel(attr.type)}
        </span>
      </div>

      <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={attr.allow_nulls}
          onChange={(e) => onUpdate(index, "allow_nulls", e.target.checked)}
          className="h-4 w-4 cursor-pointer rounded-sm border-border bg-background/70 accent-primary"
        />
        Allow Nulls
        {attr.allow_nulls && (
          <span className="font-semibold text-foreground">
            ({attr.null_percentage}%)
          </span>
        )}
      </label>

      {attr.allow_nulls && (
        <input
          type="range"
          min={1}
          max={50}
          value={attr.null_percentage}
          onChange={(e) =>
            onUpdate(index, "null_percentage", Number(e.target.value))
          }
          className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-border accent-primary"
        />
      )}

      {showMinMax && (
        <div className="flex gap-2">
          <input
            type="number"
            className="w-full rounded-md border border-border bg-background/70 px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="Min"
            value={attr.min}
            onChange={(e) => onUpdate(index, "min", e.target.value)}
          />
          <input
            type="number"
            className="w-full rounded-md border border-border bg-background/70 px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="Max"
            value={attr.max}
            onChange={(e) => onUpdate(index, "max", e.target.value)}
          />
        </div>
      )}

      {showCats && (
        <input
          className="w-full rounded-md border border-border bg-background/70 px-3 py-1.5 text-xs text-foreground placeholder-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
          placeholder="cat1, cat2, cat3"
          value={attr.categories}
          onChange={(e) => onUpdate(index, "categories", e.target.value)}
        />
      )}
    </div>
  );
}
