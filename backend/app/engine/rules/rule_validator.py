"""Semantic rule validation helpers and generated-data validator."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.engine.rules.rule_engine import SemanticRuleEngine, validate_semantic_rules

CONFIDENCE_THRESHOLD = 0.7


class SemanticRuleValidator:
    """Validates that generated data follows semantic rules."""

    @staticmethod
    def validate_rules(
        df: pd.DataFrame,
        semantic_rules: list[dict[str, Any]],
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> dict[str, Any]:
        validation_report: dict[str, Any] = {
            "rules_checked": 0,
            "rules_passed": 0,
            "rules_failed": 0,
            "violations": [],
            "detailed_results": [],
            "validation_score": 1.0,
        }

        if df.empty or not semantic_rules:
            return validation_report

        rules_to_validate = [
            r for r in semantic_rules if r.get("confidence", 0) >= confidence_threshold
        ]

        if not rules_to_validate:
            return validation_report

        validation_report["rules_checked"] = len(rules_to_validate)

        for rule in rules_to_validate:
            target = rule.get("target")
            sources = rule.get("sources", [])

            if not target or target not in df.columns:
                continue

            if not all(src in df.columns for src in sources):
                continue

            result = SemanticRuleValidator._validate_single_rule(df, rule)

            validation_report["detailed_results"].append(
                {
                    "rule_id": rule.get("id", "unknown"),
                    "target": target,
                    "validation_score": result["score"],
                    "rows_validated": result["rows_validated"],
                    "rows_passed": result["rows_passed"],
                    "violations_count": len(result["violations"]),
                }
            )

            if result["score"] >= 0.9:
                validation_report["rules_passed"] += 1
            else:
                validation_report["rules_failed"] += 1
                validation_report["violations"].extend(result["violations"][:5])

        if validation_report["rules_checked"] > 0:
            passed_score = (
                validation_report["rules_passed"] / validation_report["rules_checked"]
            )
            validation_report["validation_score"] = round(passed_score, 3)

        return validation_report

    @staticmethod
    def _validate_single_rule(
        df: pd.DataFrame,
        rule: dict[str, Any],
    ) -> dict[str, Any]:
        target = rule.get("target")

        rows_validated = 0
        rows_passed = 0
        violations: list[dict[str, Any]] = []

        for idx, row in df.iterrows():
            row_context = row.to_dict()

            if pd.isna(row.get(target)):
                continue

            rows_validated += 1

            try:
                expected_value = SemanticRuleEngine.apply_rule(rule, row_context)
                actual_value = row.get(target)

                if expected_value is None and pd.isna(actual_value):
                    rows_passed += 1
                elif expected_value is not None and actual_value is not None:
                    expected_str = str(expected_value).strip().lower()
                    actual_str = str(actual_value).strip().lower()

                    if expected_str == actual_str:
                        rows_passed += 1
                    else:
                        violations.append(
                            {
                                "row_index": idx,
                                "expected": expected_value,
                                "actual": actual_value,
                            }
                        )
            except Exception as exc:
                violations.append(
                    {
                        "row_index": idx,
                        "error": str(exc),
                    }
                )

        score = 0.0
        if rows_validated > 0:
            score = rows_passed / rows_validated

        return {
            "score": round(score, 3),
            "rows_validated": rows_validated,
            "rows_passed": rows_passed,
            "violations": violations,
        }

    @staticmethod
    def get_validation_flags(validation_report: dict[str, Any]) -> dict[str, bool]:
        return {
            "all_rules_passed": validation_report["rules_failed"] == 0,
            "high_quality": validation_report["validation_score"] >= 0.85,
            "acceptable_quality": validation_report["validation_score"] >= 0.7,
            "low_quality": validation_report["validation_score"] < 0.7,
            "any_violations": len(validation_report["violations"]) > 0,
        }


__all__ = ["validate_semantic_rules", "SemanticRuleValidator"]
