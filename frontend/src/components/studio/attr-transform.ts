import type { AttributeConfig, AttributeSuggestion } from "@/lib/api-client";

import { NUMERIC_TYPES } from "./constants";
import type { AttrRow } from "./types";
import { uid } from "./studio-helpers";

export function attrRowToApiAttribute(attr: AttrRow): AttributeConfig {
  let distribution = attr.distribution;
  if (attr.type === "categorical") {
    // Categorical allows all defined distributions, including weighted.
  } else if (NUMERIC_TYPES.includes(attr.type)) {
    if (distribution === "weighted_categorical") {
      distribution = "uniform";
    }
  } else {
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
    if (distribution === "weighted_categorical" && attr.weights.trim()) {
      const parsed = attr.weights
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map(Number);
      if (parsed.length > 0 && parsed.every((n) => !isNaN(n))) {
        constraints.weights = parsed;
      }
    }
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

export const toApiAttr = attrRowToApiAttribute;

export function applySuggestionToAttr(
  attr: AttrRow,
  suggestion: AttributeSuggestion,
): AttrRow {
  const constraints = suggestion.suggested_constraints ?? {};
  const next: AttrRow = {
    ...attr,
    distribution: suggestion.suggested_distribution,
  };

  if (typeof constraints.min === "number") next.min = String(constraints.min);
  if (typeof constraints.max === "number") next.max = String(constraints.max);
  if (typeof constraints.precision === "number") {
    next.precision = String(constraints.precision);
  }
  if (
    constraints.skew_direction === "left" ||
    constraints.skew_direction === "right"
  ) {
    next.skew_direction = constraints.skew_direction;
  }
  if (typeof constraints.skew_intensity === "number") {
    next.skew_intensity = String(constraints.skew_intensity);
  }
  if (typeof constraints.max_length === "number") {
    next.max_length = String(constraints.max_length);
  }
  if (Array.isArray(constraints.weights)) {
    next.weights = constraints.weights.map((value) => String(value)).join(", ");
  }

  return next;
}

export function templateColumnsToAttrRows(
  columns: Record<string, any>,
): AttrRow[] {
  return Object.entries(columns).map(([name, colConfig]) => {
    const dist = colConfig.distribution || {};
    const makeRow = (overrides: Partial<AttrRow>): AttrRow => ({
      _id: uid(),
      name: "field",
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
      ...overrides,
    });

    let fieldType: AttrRow["type"] = "text";
    if (colConfig.data_type === "integer") fieldType = "integer";
    else if (colConfig.data_type === "float") fieldType = "float";
    else if (colConfig.data_type === "boolean") fieldType = "boolean";
    else if (colConfig.data_type === "date") fieldType = "date";
    else if (colConfig.data_type === "email") fieldType = "email";
    else if (colConfig.data_type === "categorical") fieldType = "categorical";
    else if (colConfig.data_type === "text") fieldType = "text";

    const row: AttrRow = makeRow({
      name,
      type: fieldType,
    });

    if (dist.max_length) row.max_length = String(dist.max_length);
    if (dist.min !== undefined) row.min = String(dist.min);
    if (dist.max !== undefined) row.max = String(dist.max);
    if (dist.start_date) row.start_date = dist.start_date;
    if (dist.end_date) row.end_date = dist.end_date;
    if (dist.precision) row.precision = String(dist.precision);

    if (dist.categories && Array.isArray(dist.categories)) {
      row.categories = dist.categories.join(", ");
      row.distribution = "weighted_categorical";
      if (dist.probabilities && Array.isArray(dist.probabilities)) {
        row.weights = dist.probabilities.join(", ");
      }
    }

    return row;
  });
}
