"use client";

import { useEffect, useMemo, useState } from "react";
import { FlaskConical, Sparkles, Plus, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type {
  DryRunSemanticRulesResponse,
  SemanticConflictPolicy,
  SemanticRule,
  SemanticRulesMetadata,
} from "@/lib/api-client";

interface SemanticRuleBuilderProps {
  attributeNames: string[];
  rules: SemanticRule[];
  conflictPolicy: SemanticConflictPolicy;
  metadata: SemanticRulesMetadata | null;
  dryRunResult: DryRunSemanticRulesResponse | null;
  onChange: (rules: SemanticRule[]) => void;
  onConflictPolicyChange: (policy: SemanticConflictPolicy) => void;
  onSave: () => Promise<void>;
  onDryRun: () => Promise<void>;
  onInfer: () => Promise<void>;
  saveDisabled?: boolean;
  saveBusy?: boolean;
  dryRunBusy?: boolean;
  inferBusy?: boolean;
}

const defaultCityStateMap = {
  Mumbai: "Maharashtra",
  Bengaluru: "Karnataka",
  Delhi: "Delhi",
  Jaipur: "Rajasthan",
  Chennai: "Tamil Nadu",
};

const defaultCompanyDomainMap = {
  Google: "google.com",
  Microsoft: "microsoft.com",
  Amazon: "amazon.com",
  Infosys: "infosys.com",
  Tata: "tata.com",
};

const createRuleId = (): string => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `rule_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
};

export function SemanticRuleBuilder({
  attributeNames,
  rules,
  conflictPolicy,
  metadata,
  dryRunResult,
  onChange,
  onConflictPolicyChange,
  onSave,
  onDryRun,
  onInfer,
  saveDisabled = false,
  saveBusy = false,
  dryRunBusy = false,
  inferBusy = false,
}: SemanticRuleBuilderProps) {
  const [domainPoolText, setDomainPoolText] = useState(
    "gmail.com, yahoo.com, outlook.com",
  );
  const [jsonText, setJsonText] = useState(JSON.stringify(rules, null, 2));
  const [jsonError, setJsonError] = useState("");

  useEffect(() => {
    setJsonText(JSON.stringify(rules, null, 2));
  }, [rules]);

  const normalizedNames = useMemo(
    () => attributeNames.map((name) => name.trim()).filter(Boolean),
    [attributeNames],
  );

  const sourceGuess = (candidates: string[]): string => {
    const lower = normalizedNames.map((name) => ({
      raw: name,
      normalized: name.toLowerCase(),
    }));
    for (const candidate of candidates) {
      const hit = lower.find((item) => item.normalized.includes(candidate));
      if (hit) return hit.raw;
    }
    return normalizedNames[0] ?? "";
  };

  const targetGuess = (candidates: string[]): string => {
    const lower = normalizedNames.map((name) => ({
      raw: name,
      normalized: name.toLowerCase(),
    }));
    for (const candidate of candidates) {
      const hit = lower.find((item) => item.normalized.includes(candidate));
      if (hit) return hit.raw;
    }
    return normalizedNames[1] ?? normalizedNames[0] ?? "";
  };

  const syncJson = (nextRules: SemanticRule[]) => {
    onChange(nextRules);
    setJsonText(JSON.stringify(nextRules, null, 2));
    setJsonError("");
  };

  const addNameEmailTemplate = () => {
    const source = sourceGuess(["name", "full_name", "person"]);
    const target = targetGuess(["email", "mail"]);
    if (!source || !target) return;

    const domains = domainPoolText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    const next: SemanticRule[] = [
      ...rules,
      {
        id: createRuleId(),
        type: "name_email_template",
        target,
        sources: [source],
        transform: {
          type: "template",
          template: "{first}.{last}@{domain}",
          extractors: {
            first: `split(${source})[0]`,
            last: `split(${source})[-1]`,
          },
          domain_pool: domains.length > 0 ? domains : ["gmail.com"],
        },
        confidence: 0.9,
        priority: 1,
        constraints: {
          lowercase: true,
          no_spaces: true,
        },
      },
    ];

    syncJson(next);
  };

  const addCityStateMapping = () => {
    const source = sourceGuess(["city", "town"]);
    const target = targetGuess(["state", "province", "region"]);
    if (!source || !target) return;

    const next: SemanticRule[] = [
      ...rules,
      {
        id: createRuleId(),
        type: "city_state_mapping",
        target,
        sources: [source],
        transform: {
          type: "mapping",
          mapping_table: defaultCityStateMap,
        },
        confidence: 0.85,
        priority: 2,
        constraints: null,
      },
    ];

    syncJson(next);
  };

  const addCompanyDomainMapping = () => {
    const source = sourceGuess(["company", "organization", "org"]);
    const target = targetGuess(["domain", "email_domain", "website"]);
    if (!source || !target) return;

    const next: SemanticRule[] = [
      ...rules,
      {
        id: createRuleId(),
        type: "company_domain_mapping",
        target,
        sources: [source],
        transform: {
          type: "mapping",
          mapping_table: defaultCompanyDomainMap,
        },
        confidence: 0.82,
        priority: 2,
        constraints: null,
      },
    ];

    syncJson(next);
  };

  const removeRule = (id: string) => {
    syncJson(rules.filter((rule) => rule.id !== id));
  };

  const applyJsonText = () => {
    try {
      const parsed = JSON.parse(jsonText) as unknown;
      if (!Array.isArray(parsed)) {
        throw new Error("Rules JSON must be an array");
      }

      const nextRules = parsed
        .filter(
          (item): item is Record<string, unknown> =>
            !!item && typeof item === "object",
        )
        .map(
          (item): SemanticRule => ({
            id: String(item.id ?? createRuleId()),
            type: String(item.type ?? "custom_rule"),
            target: String(item.target ?? "").trim(),
            sources: Array.isArray(item.sources)
              ? item.sources.map((s) => String(s)).filter(Boolean)
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
          }),
        )
        .filter((rule) => rule.target && rule.sources.length > 0);

      syncJson(nextRules);
    } catch (error) {
      setJsonError(error instanceof Error ? error.message : "Invalid JSON");
    }
  };

  return (
    <Card className="mb-8 border-border bg-card/70 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">
            Semantic Rules
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Use templates to quickly create intelligent cross-column behavior.
          </p>
        </div>
        <Button
          type="button"
          variant="default"
          onClick={() => void onSave()}
          disabled={saveDisabled || saveBusy}
        >
          <Save className="mr-2 h-4 w-4" />
          {saveBusy ? "Saving Rules..." : "Save Rules"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => void onDryRun()}
          disabled={saveDisabled || dryRunBusy}
        >
          <FlaskConical className="mr-2 h-4 w-4" />
          {dryRunBusy ? "Dry Run..." : "Dry Run"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => void onInfer()}
          disabled={saveDisabled || inferBusy}
        >
          <Sparkles className="mr-2 h-4 w-4" />
          {inferBusy ? "Inferring..." : "Infer Rules"}
        </Button>
      </div>

      <div className="mb-4 grid gap-3 rounded-lg border border-border/60 bg-background/40 p-3 md:grid-cols-[220px_1fr]">
        <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Conflict Policy
        </label>
        <select
          value={conflictPolicy}
          onChange={(event) =>
            onConflictPolicyChange(event.target.value as SemanticConflictPolicy)
          }
          className="h-10 rounded-md border border-border bg-background px-3 text-sm"
        >
          <option value="priority_wins">
            priority_wins (lowest priority value wins)
          </option>
          <option value="last_write_wins">
            last_write_wins (last sorted rule wins)
          </option>
        </select>
      </div>

      {metadata ? (
        <div className="mb-4 rounded-lg border border-border/60 bg-background/40 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Validation & Execution
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Policy: {metadata.conflict_policy ?? "priority_wins"} | Rules:{" "}
            {metadata.rule_count ?? rules.length}
          </p>
          {Array.isArray(metadata.execution_order) &&
          metadata.execution_order.length > 0 ? (
            <p className="mt-1 text-xs text-muted-foreground">
              Execution order: {metadata.execution_order.join(" -> ")}
            </p>
          ) : null}
          {Array.isArray(metadata.warnings) && metadata.warnings.length > 0 ? (
            <div className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-200">
              {metadata.warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          ) : null}
          {Array.isArray(metadata.errors) && metadata.errors.length > 0 ? (
            <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
              {metadata.errors.map((error) => (
                <p key={error}>{error}</p>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {dryRunResult ? (
        <div className="mb-4 rounded-lg border border-border/60 bg-background/40 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Dry-Run Summary
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Rows changed: {dryRunResult.metadata.changed_rows ?? 0} | Cells
            changed: {dryRunResult.metadata.changed_cells ?? 0}
          </p>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-3 rounded-lg border border-border/60 bg-background/40 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Rule Templates
          </p>

          <label className="text-xs text-muted-foreground">
            Name/email domains (comma-separated)
          </label>
          <input
            className="w-full"
            value={domainPoolText}
            onChange={(e) => setDomainPoolText(e.target.value)}
          />

          <div className="grid gap-2 pt-1">
            <Button
              type="button"
              variant="outline"
              onClick={addNameEmailTemplate}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Name -&gt; Email Template
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={addCityStateMapping}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add City -&gt; State Mapping
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={addCompanyDomainMapping}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Company -&gt; Domain Mapping
            </Button>
          </div>

          <div className="space-y-2 pt-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Active Rules ({rules.length})
            </p>
            {rules.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No semantic rules yet. Add one from templates.
              </p>
            ) : (
              rules.map((rule) => (
                <div
                  key={rule.id}
                  className="rounded-md border border-border/60 bg-background/70 p-2"
                >
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="truncate text-foreground">
                      {rule.sources.join(", ")} -&gt; {rule.target}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeRule(rule.id)}
                      className="rounded p-1 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                      aria-label="Remove semantic rule"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {rule.type} | confidence={rule.confidence.toFixed(2)} |
                    priority={rule.priority}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="space-y-2 rounded-lg border border-border/60 bg-background/40 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Advanced JSON Editor
          </p>
          <textarea
            className="h-[340px] w-full font-mono text-xs"
            value={jsonText}
            onChange={(e) => {
              setJsonText(e.target.value);
              setJsonError("");
            }}
          />
          {jsonError ? (
            <p className="text-xs text-destructive">{jsonError}</p>
          ) : null}
          <Button type="button" variant="secondary" onClick={applyJsonText}>
            Apply JSON
          </Button>
        </div>
      </div>
    </Card>
  );
}
