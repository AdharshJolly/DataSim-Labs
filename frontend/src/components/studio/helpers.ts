import type { AttributeConfig, DataType } from "@/lib/api-client";
import { NUMERIC_TYPES, ALL_TYPE_OPTIONS } from "./constants";
import type { AttrRow } from "./types";

let _uid = 0;

/**
 * Validates that a categorical field's weights string is consistent with its
 * categories string. Returns a human-readable error or null if valid.
 */
export function validateCategoricalWeights(attr: AttrRow): string | null {
  if (attr.type !== "categorical" || attr.distribution !== "weighted_categorical") {
    return null;
  }
  if (!attr.weights.trim()) return null; // weights are optional

  const cats = attr.categories
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const rawWeights = attr.weights
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  if (rawWeights.length === 0) return null;

  const weights = rawWeights.map(Number);
  if (weights.some(isNaN)) {
    return `"${attr.name}": weights must be numbers, got: ${rawWeights.filter((_, i) => isNaN(weights[i])).join(", ")}`;
  }
  if (weights.some((w) => w < 0)) {
    return `"${attr.name}": weights must be non-negative`;
  }
  if (cats.length > 0 && weights.length !== cats.length) {
    return `"${attr.name}": ${cats.length} categories but ${weights.length} weights — counts must match`;
  }
  return null;
}

export function uid(): string {
  return `attr-${Date.now()}-${++_uid}`;
}

export function newAttr(index: number): AttrRow {
  return {
    _id: uid(),
    name: `field_${index + 1}`,
    description: "",
    type: "integer",
    distribution: "uniform",
    allow_nulls: false,
    null_percentage: 10,
    min: "0",
    max: "100",
    categories: "",
    weights: "",
    start_date: "",
    end_date: "",
    precision: "2",
    max_length: "64",
    true_probability: "0.5",
    skew_direction: "right",
    skew_intensity: "2",
  };
}

export function toApiAttr(attr: AttrRow): AttributeConfig {
  let distribution = attr.distribution;
  if (attr.type === "categorical") {
    // Categorical allows all defined distributions, including weighted.
  } else if (NUMERIC_TYPES.includes(attr.type)) {
    if (distribution === "weighted_categorical") {
      distribution = "uniform";
    }
  } else {
    // Non-numeric/non-categorical types only support uniform server-side.
    distribution = "uniform";
  }

  const constraints: Record<string, unknown> = {};
  if (NUMERIC_TYPES.includes(attr.type)) {
    if (attr.min !== "") constraints.min = Number(attr.min);
    if (attr.max !== "") constraints.max = Number(attr.max);
    if (attr.type === "float" && attr.precision !== "") {
      constraints.precision = parseInt(attr.precision, 10);
    }
    if (distribution === "skewed") {
      constraints.skew_direction = attr.skew_direction;
      if (attr.skew_intensity !== "") {
        constraints.skew_intensity = Number(attr.skew_intensity);
      }
    }
  } else if (attr.type === "categorical" && attr.categories.trim()) {
    constraints.categories = attr.categories
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (
      distribution === "weighted_categorical" &&
      attr.weights.trim()
    ) {
      const parsed = attr.weights
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map(Number);
      if (parsed.length > 0 && parsed.every((n) => !isNaN(n))) {
        constraints.weights = parsed;
      }
    }
  } else if (attr.type === "categorical") {
    // No categories entered yet — leave constraints empty.
  } else if (attr.type === "date") {
    if (attr.start_date) constraints.start_date = attr.start_date;
    if (attr.end_date) constraints.end_date = attr.end_date;
  } else if (attr.type === "text") {
    if (attr.max_length !== "") {
      constraints.max_length = parseInt(attr.max_length, 10);
    }
  } else if (attr.type === "boolean") {
    if (attr.true_probability !== "") {
      constraints.true_probability = Number(attr.true_probability);
    }
  }
  return {
    name: attr.name.trim() || `field_${Math.random().toString(36).slice(2, 6)}`,
    description: attr.description,
    type: attr.type,
    distribution,
    null_percentage: attr.allow_nulls ? attr.null_percentage : 0,
    constraints,
  };
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function typeLabel(t: DataType): string {
  return ALL_TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t;
}
