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
    <div className="sk-panel space-y-3 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-semibold">{attr.name}</span>
        <span className="sk-chip flex-shrink-0">{typeLabel(attr.type)}</span>
      </div>

      <label className="flex cursor-pointer items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
        <input
          type="checkbox"
          checked={attr.allow_nulls}
          onChange={(e) => onUpdate(index, "allow_nulls", e.target.checked)}
          className="accent-[hsl(var(--primary))]"
        />
        Nulls{" "}
        {attr.allow_nulls && (
          <span className="font-semibold text-[hsl(var(--foreground))]">
            {attr.null_percentage}%
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
          className="w-full accent-[hsl(var(--primary))]"
        />
      )}

      {showMinMax && (
        <div className="flex gap-2">
          <input
            type="number"
            className="sk-input py-1 text-xs"
            placeholder="Min"
            value={attr.min}
            onChange={(e) => onUpdate(index, "min", e.target.value)}
          />
          <input
            type="number"
            className="sk-input py-1 text-xs"
            placeholder="Max"
            value={attr.max}
            onChange={(e) => onUpdate(index, "max", e.target.value)}
          />
        </div>
      )}

      {showCats && (
        <input
          className="sk-input py-1 text-xs"
          placeholder="cat1, cat2, cat3"
          value={attr.categories}
          onChange={(e) => onUpdate(index, "categories", e.target.value)}
        />
      )}
    </div>
  );
}
