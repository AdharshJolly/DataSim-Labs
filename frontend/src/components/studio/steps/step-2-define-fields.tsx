import { LoaderCircle, Plus } from "lucide-react";

import { AttrCard } from "@/components/studio/attr-card";
import {
  RelationshipBuilder,
  type CorrelationRule,
} from "@/components/studio/relationship-builder";
import { SemanticRuleBuilder } from "@/components/studio/semantic-rule-builder";
import type { AttrRow, AttrUpdate, Step } from "@/components/studio/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  type DryRunSemanticRulesResponse,
  type SemanticConflictPolicy,
  type SemanticRule,
  type SemanticRulesMetadata,
} from "@/lib/api-client";

interface Step2DefineFieldsProps {
  attrs: AttrRow[];
  busy: boolean;
  suggestionsBusy: boolean;
  versionId: string;
  correlationRules: CorrelationRule[];
  semanticRules: SemanticRule[];
  semanticConflictPolicy: SemanticConflictPolicy;
  semanticRuleMetadata: SemanticRulesMetadata | null;
  semanticDryRunResult: DryRunSemanticRulesResponse | null;
  semanticRulesSaving: boolean;
  semanticRulesDryRunning: boolean;
  semanticRulesInferring: boolean;
  correlationRulesText: string;
  onSuggestSettings: () => Promise<void>;
  onSaveAndPreview: () => Promise<void>;
  onSetStep: (step: Step) => void;
  onCorrelationRulesChange: (rules: CorrelationRule[]) => void;
  onSemanticRulesChange: (rules: SemanticRule[]) => void;
  onSemanticConflictPolicyChange: (policy: SemanticConflictPolicy) => void;
  onSaveSemanticRules: () => Promise<void>;
  onDryRunSemanticRules: () => Promise<void>;
  onInferSemanticRules: () => Promise<void>;
  onCorrelationRulesTextChange: (value: string) => void;
  onAddAttr: () => void;
  onUpdateAttr: AttrUpdate;
  onRemoveAttr: (i: number) => void;
}

export function Step2DefineFields({
  attrs,
  busy,
  suggestionsBusy,
  versionId,
  correlationRules,
  semanticRules,
  semanticConflictPolicy,
  semanticRuleMetadata,
  semanticDryRunResult,
  semanticRulesSaving,
  semanticRulesDryRunning,
  semanticRulesInferring,
  correlationRulesText,
  onSuggestSettings,
  onSaveAndPreview,
  onSetStep,
  onCorrelationRulesChange,
  onSemanticRulesChange,
  onSemanticConflictPolicyChange,
  onSaveSemanticRules,
  onDryRunSemanticRules,
  onInferSemanticRules,
  onCorrelationRulesTextChange,
  onAddAttr,
  onUpdateAttr,
  onRemoveAttr,
}: Step2DefineFieldsProps) {
  return (
    <div>
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold">
            Define Your Fields
          </h1>
          <p className="mt-2 text-muted-foreground">
            Each field becomes a column. Describe what it represents to guide
            generation - the more detail, the better.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            className="whitespace-nowrap"
            disabled={busy || suggestionsBusy || attrs.length === 0}
            onClick={() => void onSuggestSettings()}
          >
            {suggestionsBusy ? (
              <span className="flex items-center justify-center gap-2">
                <LoaderCircle className="h-4 w-4 animate-spin" /> Suggesting…
              </span>
            ) : (
              "Suggest Settings"
            )}
          </Button>
          <Button
            type="button"
            variant="default"
            className="whitespace-nowrap"
            disabled={busy || attrs.length === 0}
            onClick={() => void onSaveAndPreview()}
          >
            {busy ? (
              <span className="flex items-center justify-center gap-2">
                <LoaderCircle className="h-4 w-4 animate-spin" /> Saving…
              </span>
            ) : (
              "Save & Preview →"
            )}
          </Button>
        </div>
      </header>

      <RelationshipBuilder
        attributeNames={attrs.map((attr) => attr.name)}
        rules={correlationRules}
        onChange={onCorrelationRulesChange}
      />

      <SemanticRuleBuilder
        attributeNames={attrs.map((attr) => attr.name)}
        rules={semanticRules}
        conflictPolicy={semanticConflictPolicy}
        metadata={semanticRuleMetadata}
        dryRunResult={semanticDryRunResult}
        onChange={onSemanticRulesChange}
        onConflictPolicyChange={onSemanticConflictPolicyChange}
        onSave={onSaveSemanticRules}
        onDryRun={onDryRunSemanticRules}
        onInfer={onInferSemanticRules}
        saveDisabled={!versionId}
        saveBusy={semanticRulesSaving}
        dryRunBusy={semanticRulesDryRunning}
        inferBusy={semanticRulesInferring}
      />

      <Card className="mb-8 border-border bg-card/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Advanced JSON Editor (optional)
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          You can still edit relationships as raw JSON.
        </p>
        <textarea
          className="mt-3 h-28 w-full"
          value={correlationRulesText}
          onChange={(e) => onCorrelationRulesTextChange(e.target.value)}
        />
      </Card>

      <div className="space-y-4">
        {attrs.map((attr, i) => (
          <AttrCard
            key={attr._id}
            attr={attr}
            index={i}
            total={attrs.length}
            onUpdate={onUpdateAttr}
            onRemove={onRemoveAttr}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={onAddAttr}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border py-4 text-sm font-semibold text-muted-foreground transition-all hover:border-primary/80 hover:bg-primary/10 hover:text-primary"
      >
        <Plus className="h-4 w-4" />
        Add Field
      </button>

      <div className="mt-8 flex items-center gap-3">
        <Button
          type="button"
          variant="default"
          disabled={busy || attrs.length === 0}
          onClick={() => void onSaveAndPreview()}
        >
          {busy ? "Saving…" : "Save & Preview →"}
        </Button>
        <Button type="button" variant="outline" onClick={() => onSetStep(1)}>
          ← Back
        </Button>
      </div>
    </div>
  );
}
