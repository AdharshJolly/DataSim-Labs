import { useMemo } from "react";

import {
  parseCorrelationRulesText,
  parseSemanticRulesText,
} from "@/components/studio/rule-parsers";
import type { CorrelationRule } from "@/components/studio/relationship-builder";
import type { SemanticRule } from "@/lib/api-client";

interface UseStudioRulesArgs {
  correlationRulesText: string;
  semanticRulesText: string;
  setCorrelationRulesText: (value: string) => void;
  setSemanticRulesText: (value: string) => void;
  setSemanticDryRunResult: (value: null) => void;
}

export function useStudioRules({
  correlationRulesText,
  semanticRulesText,
  setCorrelationRulesText,
  setSemanticRulesText,
  setSemanticDryRunResult,
}: UseStudioRulesArgs) {
  const correlationRules: CorrelationRule[] = useMemo(() => {
    try {
      return parseCorrelationRulesText(correlationRulesText);
    } catch {
      return [];
    }
  }, [correlationRulesText]);

  const semanticRules: SemanticRule[] = useMemo(() => {
    try {
      return parseSemanticRulesText(semanticRulesText);
    } catch {
      return [];
    }
  }, [semanticRulesText]);

  const parseCorrelationRules = () =>
    parseCorrelationRulesText(correlationRulesText);

  const handleCorrelationRulesChange = (rules: CorrelationRule[]) => {
    setCorrelationRulesText(JSON.stringify(rules, null, 2));
  };

  const handleSemanticRulesChange = (rules: SemanticRule[]) => {
    setSemanticRulesText(JSON.stringify(rules, null, 2));
    setSemanticDryRunResult(null);
  };

  return {
    correlationRules,
    semanticRules,
    parseCorrelationRules,
    handleCorrelationRulesChange,
    handleSemanticRulesChange,
  };
}
