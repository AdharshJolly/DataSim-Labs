import { Trash2, GripVertical, ChevronDown, ChevronUp } from "lucide-react";
import type { DataType, DistributionType } from "@/lib/api-client";
import { useState } from "react";
import { ThemedDropdown } from "@/components/ui/themed-dropdown";

import {
  DIST_OPTIONS,
  DIST_TYPES,
  NUMERIC_TYPES,
  TYPE_OPTIONS,
} from "./constants";
import type { AttrRow, AttrUpdate } from "./types";

interface AttrCardProps {
  attr: AttrRow;
  index: number;
  total: number;
  onUpdate: AttrUpdate;
  onRemove: (i: number) => void;
}

export function AttrCard({
  attr,
  index,
  total,
  onUpdate,
  onRemove,
}: AttrCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const showDist = DIST_TYPES.includes(attr.type);
  const distributionOptions =
    attr.type === "categorical"
      ? DIST_OPTIONS
      : DIST_OPTIONS.filter(
          (option) => option.value !== "weighted_categorical",
        );
  const typeDropdownOptions = TYPE_OPTIONS.flatMap((group) =>
    group.options.map((option) => ({
      value: option.value,
      label: option.label,
      description: `${group.category} • ${option.description}`,
      icon: <option.icon className="h-3.5 w-3.5" />,
    })),
  );
  const distributionDropdownOptions = distributionOptions.map((option) => ({
    value: option.value,
    label: option.label,
  }));
  const showMinMax = NUMERIC_TYPES.includes(attr.type);
  const showCats = attr.type === "categorical";
  const showDates = attr.type === "date";
  const showPrecision = attr.type === "float";
  const showMaxLength = attr.type === "text";
  const showTrueProbability = attr.type === "boolean";
  const showWeights =
    attr.type === "categorical" && attr.distribution === "weighted_categorical";
  const showSkewParams =
    NUMERIC_TYPES.includes(attr.type) && attr.distribution === "skewed";
  const hasSettings =
    showDist ||
    showMinMax ||
    showCats ||
    showDates ||
    showPrecision ||
    showMaxLength ||
    showTrueProbability ||
    showSkewParams;

  return (
    <div className="rounded-lg border border-border bg-gradient-to-br from-card/80 to-transparent backdrop-blur-[2px] transition-all duration-300 focus-within:border-primary/80 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/10">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border p-3">
        <GripVertical className="h-5 w-5 flex-shrink-0 cursor-move text-muted-foreground/50" />
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-border text-xs font-bold text-muted-foreground">
          {index + 1}
        </span>
        <input
          className="flex-1 bg-transparent text-sm font-semibold text-foreground placeholder-muted-foreground/60 focus:outline-none"
          value={attr.name}
          placeholder="field_name"
          onChange={(e) => onUpdate(index, "name", e.target.value)}
          spellCheck={false}
        />

        <div className="ml-auto w-64">
          <ThemedDropdown
            id={`attr-${index}-type`}
            value={attr.type}
            options={typeDropdownOptions}
            placeholder="Select type"
            onChange={(nextValue) =>
              onUpdate(index, "type", nextValue as DataType)
            }
            buttonClassName="h-8 rounded-md bg-background/50 px-2.5 text-xs"
            menuClassName="max-h-[320px]"
            optionClassName="py-2"
          />
        </div>

        {hasSettings && (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex-shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        )}
        {total > 1 && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="flex-shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-destructive/20 hover:text-destructive"
            aria-label={`Remove ${attr.name}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Body */}
      {isExpanded && (
        <div className="space-y-4 p-4">
          <input
            className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground placeholder-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="Describe this field — e.g. 'Patient age in years, range 18-90'"
            value={attr.description}
            onChange={(e) => onUpdate(index, "description", e.target.value)}
          />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {showDist && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Distribution
                </label>
                <ThemedDropdown
                  id={`attr-${index}-distribution`}
                  value={attr.distribution}
                  options={distributionDropdownOptions}
                  placeholder="Select distribution"
                  onChange={(nextValue) =>
                    onUpdate(
                      index,
                      "distribution",
                      nextValue as DistributionType,
                    )
                  }
                  buttonClassName="h-10 rounded-md bg-background/70"
                  menuClassName="max-h-[220px]"
                  optionClassName="py-2"
                />
              </div>
            )}

            <div className="space-y-1.5">
              <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-muted-foreground">
                <input
                  type="checkbox"
                  checked={attr.allow_nulls}
                  onChange={(e) =>
                    onUpdate(index, "allow_nulls", e.target.checked)
                  }
                  className="h-4 w-4 cursor-pointer rounded-sm border-border bg-background/70 accent-primary"
                />
                Allow Null Values
              </label>
              {attr.allow_nulls && (
                <div className="mt-2 flex items-center gap-3">
                  <input
                    type="range"
                    min={1}
                    max={50}
                    value={attr.null_percentage}
                    onChange={(e) =>
                      onUpdate(index, "null_percentage", Number(e.target.value))
                    }
                    className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                  />
                  <span className="w-10 text-right text-sm font-semibold text-foreground">
                    {attr.null_percentage}%
                  </span>
                </div>
              )}
            </div>
          </div>

          {showMinMax && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Min value
                </label>
                <input
                  type="number"
                  className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="0"
                  value={attr.min}
                  onChange={(e) => onUpdate(index, "min", e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Max value
                </label>
                <input
                  type="number"
                  className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="100"
                  value={attr.max}
                  onChange={(e) => onUpdate(index, "max", e.target.value)}
                />
              </div>
            </div>
          )}

          {showPrecision && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Decimal Precision
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={10}
                  value={attr.precision}
                  onChange={(e) => onUpdate(index, "precision", e.target.value)}
                  className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                />
                <span className="w-8 text-right text-sm font-semibold text-foreground">
                  {attr.precision}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground/70">
                Number of digits after the decimal point
              </p>
            </div>
          )}

          {showMaxLength && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Max Length
              </label>
              <input
                type="number"
                min={1}
                className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="64"
                value={attr.max_length}
                onChange={(e) => onUpdate(index, "max_length", e.target.value)}
              />
              <p className="text-[10px] text-muted-foreground/70">
                Maximum character length for generated text
              </p>
            </div>
          )}

          {showTrueProbability && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                True Probability
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={attr.true_probability}
                  onChange={(e) =>
                    onUpdate(index, "true_probability", e.target.value)
                  }
                  className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                />
                <span className="w-12 text-right text-sm font-semibold text-foreground">
                  {Number(attr.true_probability).toFixed(2)}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground/70">
                How often the value will be true (0 = always false, 1 = always
                true)
              </p>
            </div>
          )}

          {showCats && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Categories (comma-separated)
              </label>
              <input
                className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground placeholder-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="e.g. Male, Female, Non-binary"
                value={attr.categories}
                onChange={(e) => onUpdate(index, "categories", e.target.value)}
              />
            </div>
          )}

          {showWeights && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Weights (comma-separated, matching categories)
              </label>
              <input
                className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground placeholder-muted-foreground/50 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="e.g. 3, 2, 1"
                value={attr.weights}
                onChange={(e) => onUpdate(index, "weights", e.target.value)}
              />
              <p className="text-[10px] text-muted-foreground/70">
                Relative weights for each category — they don&apos;t need to sum
                to 1, they will be normalized automatically
              </p>
            </div>
          )}

          {showSkewParams && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Skew Direction
                </label>
                <div className="flex rounded-md border border-border overflow-hidden">
                  <button
                    type="button"
                    onClick={() => onUpdate(index, "skew_direction", "left")}
                    className={`flex-1 px-3 py-1.5 text-xs font-medium transition-colors ${
                      attr.skew_direction === "left"
                        ? "bg-primary/20 text-primary"
                        : "bg-background/70 text-muted-foreground hover:bg-card/70"
                    }`}
                  >
                    ← Left (tail left)
                  </button>
                  <button
                    type="button"
                    onClick={() => onUpdate(index, "skew_direction", "right")}
                    className={`flex-1 px-3 py-1.5 text-xs font-medium transition-colors ${
                      attr.skew_direction === "right"
                        ? "bg-primary/20 text-primary"
                        : "bg-background/70 text-muted-foreground hover:bg-card/70"
                    }`}
                  >
                    Right (tail right) →
                  </button>
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Skew Intensity
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0.1}
                    max={10}
                    step={0.1}
                    value={attr.skew_intensity}
                    onChange={(e) =>
                      onUpdate(index, "skew_intensity", e.target.value)
                    }
                    className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-border accent-primary"
                  />
                  <span className="w-10 text-right text-sm font-semibold text-foreground">
                    {Number(attr.skew_intensity).toFixed(1)}
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground/70">
                  Higher values produce more extreme skew
                </p>
              </div>
            </div>
          )}

          {showDates && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Start date
                </label>
                <input
                  type="date"
                  className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                  value={attr.start_date}
                  onChange={(e) =>
                    onUpdate(index, "start_date", e.target.value)
                  }
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  End date
                </label>
                <input
                  type="date"
                  className="w-full rounded-md border border-border bg-background/70 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                  value={attr.end_date}
                  onChange={(e) => onUpdate(index, "end_date", e.target.value)}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
