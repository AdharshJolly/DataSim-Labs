import type { DataType, DistributionType } from "@/lib/api-client";

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
  const showDist = DIST_TYPES.includes(attr.type);
  const distributionOptions =
    attr.type === "categorical"
      ? DIST_OPTIONS
      : DIST_OPTIONS.filter(
          (option) => option.value !== "weighted_categorical",
        );
  const showMinMax = NUMERIC_TYPES.includes(attr.type);
  const showCats = attr.type === "categorical";
  const showDates = attr.type === "date";

  return (
    <div className="attr-card">
      <div className="attr-card-header">
        <span className="attr-index-badge">{index + 1}</span>
        <input
          className="attr-name-input"
          value={attr.name}
          placeholder="field_name"
          onChange={(e) => onUpdate(index, "name", e.target.value)}
          spellCheck={false}
        />
        <select
          className="attr-type-pill ml-auto"
          value={attr.type}
          onChange={(e) => onUpdate(index, "type", e.target.value as DataType)}
        >
          {TYPE_OPTIONS.map(({ value, label, icon }) => (
            <option key={value} value={value}>
              {icon} {label}
            </option>
          ))}
        </select>
        {total > 1 && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="attr-remove-btn"
            aria-label={`Remove ${attr.name}`}
          >
            ✕
          </button>
        )}
      </div>

      <div className="attr-card-body">
        <input
          className="sk-input text-sm"
          placeholder="Describe this field — e.g. 'Patient age in years, range 18-90'"
          value={attr.description}
          onChange={(e) => onUpdate(index, "description", e.target.value)}
        />

        <div className="attr-settings-row">
          {showDist && (
            <div className="attr-field-half">
              <label className="studio-label-xs">Distribution</label>
              <select
                className="sk-select text-sm"
                value={attr.distribution}
                onChange={(e) =>
                  onUpdate(
                    index,
                    "distribution",
                    e.target.value as DistributionType,
                  )
                }
              >
                {distributionOptions.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="attr-field-half">
            <label className="studio-label-xs flex items-center gap-2">
              <input
                type="checkbox"
                checked={attr.allow_nulls}
                onChange={(e) =>
                  onUpdate(index, "allow_nulls", e.target.checked)
                }
                className="accent-[hsl(var(--primary))]"
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
                  className="flex-1 accent-[hsl(var(--primary))]"
                />
                <span className="w-10 text-right text-sm font-semibold">
                  {attr.null_percentage}%
                </span>
              </div>
            )}
          </div>
        </div>

        {showMinMax && (
          <div className="attr-settings-row">
            <div className="attr-field-half">
              <label className="studio-label-xs">Min value</label>
              <input
                type="number"
                className="sk-input text-sm"
                placeholder="0"
                value={attr.min}
                onChange={(e) => onUpdate(index, "min", e.target.value)}
              />
            </div>
            <div className="attr-field-half">
              <label className="studio-label-xs">Max value</label>
              <input
                type="number"
                className="sk-input text-sm"
                placeholder="100"
                value={attr.max}
                onChange={(e) => onUpdate(index, "max", e.target.value)}
              />
            </div>
          </div>
        )}

        {showCats && (
          <div className="studio-field">
            <label className="studio-label-xs">
              Categories{" "}
              <span className="normal-case font-normal text-[hsl(var(--muted-foreground))]">
                - comma separated
              </span>
            </label>
            <input
              className="sk-input text-sm"
              placeholder="Male, Female, Non-binary, Prefer not to say"
              value={attr.categories}
              onChange={(e) => onUpdate(index, "categories", e.target.value)}
            />
          </div>
        )}

        {showDates && (
          <div className="attr-settings-row">
            <div className="attr-field-half">
              <label className="studio-label-xs">Start date</label>
              <input
                type="date"
                className="sk-input text-sm"
                value={attr.start_date}
                onChange={(e) => onUpdate(index, "start_date", e.target.value)}
              />
            </div>
            <div className="attr-field-half">
              <label className="studio-label-xs">End date</label>
              <input
                type="date"
                className="sk-input text-sm"
                value={attr.end_date}
                onChange={(e) => onUpdate(index, "end_date", e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
