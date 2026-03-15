import type { AttributeConfig, DataType } from "@/lib/api-client";
import { NUMERIC_TYPES, TYPE_OPTIONS } from "./constants";
import type { AttrRow } from "./types";

let _uid = 0;

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
    start_date: "",
    end_date: "",
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
  } else if (attr.type === "categorical" && attr.categories.trim()) {
    constraints.categories = attr.categories
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  } else if (attr.type === "date") {
    if (attr.start_date) constraints.start_date = attr.start_date;
    if (attr.end_date) constraints.end_date = attr.end_date;
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
  return TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t;
}
