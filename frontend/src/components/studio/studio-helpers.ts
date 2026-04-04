import type { AttrRow } from "./types";

/**
 * Validates that a categorical field's weights string is consistent with its
 * categories string. Returns a human-readable error or null if valid.
 */
export function validateCategoricalWeights(attr: AttrRow): string | null {
  if (
    attr.type !== "categorical" ||
    attr.distribution !== "weighted_categorical"
  ) {
    return null;
  }
  if (!attr.weights.trim()) return null;

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
    return `"${attr.name}": ${cats.length} categories but ${weights.length} weights - counts must match`;
  }
  return null;
}
