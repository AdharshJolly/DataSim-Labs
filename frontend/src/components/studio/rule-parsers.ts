import type { SemanticRule } from "@/lib/api-client";

export function parseCorrelationRulesText(
  text: string,
): Array<{ source: string; target: string; strength: number }> {
  if (!text.trim()) {
    return [];
  }

  const parsed = JSON.parse(text) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("Correlation rules must be a JSON array.");
  }

  return parsed
    .filter(
      (item): item is Record<string, unknown> =>
        !!item && typeof item === "object",
    )
    .map((item) => ({
      source: String(item.source ?? "").trim(),
      target: String(item.target ?? "").trim(),
      strength: Number(item.strength ?? 0),
    }))
    .filter(
      (item) => item.source && item.target && !Number.isNaN(item.strength),
    );
}

export function parseSemanticRulesText(text: string): SemanticRule[] {
  if (!text.trim()) {
    return [];
  }

  const parsed = JSON.parse(text) as unknown;
  if (!Array.isArray(parsed)) {
    return [];
  }

  return parsed
    .filter(
      (item): item is Record<string, unknown> =>
        !!item && typeof item === "object",
    )
    .map((item) => ({
      id: String(item.id ?? "").trim(),
      type: String(item.type ?? "custom_rule").trim(),
      target: String(item.target ?? "").trim(),
      sources: Array.isArray(item.sources)
        ? item.sources.map((source) => String(source).trim()).filter(Boolean)
        : [],
      transform:
        item.transform && typeof item.transform === "object"
          ? (item.transform as Record<string, unknown>)
          : {},
      confidence: Number(item.confidence ?? 0.7),
      priority: Number(item.priority ?? 1),
      constraints:
        item.constraints && typeof item.constraints === "object"
          ? (item.constraints as Record<string, unknown>)
          : null,
    }))
    .filter(
      (rule) =>
        rule.id &&
        rule.target &&
        rule.sources.length > 0 &&
        !Number.isNaN(rule.confidence) &&
        !Number.isNaN(rule.priority),
    );
}

export function mergeSemanticRuleSets(
  existing: SemanticRule[],
  incoming: SemanticRule[],
): SemanticRule[] {
  const seen = new Set<string>();
  const merged: SemanticRule[] = [];

  const pushIfUnique = (rule: SemanticRule) => {
    const key = JSON.stringify({
      target: rule.target,
      sources: [...rule.sources].sort(),
      type: rule.type,
      transform: rule.transform,
    });
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    merged.push(rule);
  };

  for (const rule of existing) {
    pushIfUnique(rule);
  }
  for (const rule of incoming) {
    pushIfUnique(rule);
  }

  return merged;
}
