"""
semantic_rule_validator.py

Validates generated data against inferred semantic rules to ensure data quality.
"""

import pandas as pd
from typing import Any, Dict, List

from app.engine.rules.rule_engine import SemanticRuleEngine


CONFIDENCE_THRESHOLD = 0.7


class SemanticRuleValidator:
    """Validates that generated data follows semantic rules."""

    @staticmethod
    def validate_rules(
        df: pd.DataFrame,
        semantic_rules: List[Dict[str, Any]],
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Validate that generated data matches semantic rules.

        Returns validation report with:
        - rules_checked: number of rules validated
        - rules_passed: number of rules with high validation score
        - rules_failed: number of rules with low validation score
        - violations: list of specific violations found
        - validation_score: overall validation score [0-1]
        """
        validation_report = {
            "rules_checked": 0,
            "rules_passed": 0,
            "rules_failed": 0,
            "violations": [],
            "detailed_results": [],
            "validation_score": 1.0,
        }

        if df.empty or not semantic_rules:
            return validation_report

        # Filter rules by confidence
        rules_to_validate = [
            r for r in semantic_rules if r.get("confidence", 0) >= confidence_threshold
        ]

        if not rules_to_validate:
            return validation_report

        validation_report["rules_checked"] = len(rules_to_validate)

        for rule in rules_to_validate:
            target = rule.get("target")
            sources = rule.get("sources", [])
            confidence = rule.get("confidence", 0.5)

            if not target or target not in df.columns:
                continue

            if not all(src in df.columns for src in sources):
                continue

            # Validate the rule
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
                validation_report["violations"].extend(
                    result["violations"][:5]
                )  # Top 5

        # Calculate overall validation score
        if validation_report["rules_checked"] > 0:
            passed_score = (
                validation_report["rules_passed"] / validation_report["rules_checked"]
            )
            validation_report["validation_score"] = round(passed_score, 3)

        return validation_report

    @staticmethod
    def _validate_single_rule(
        df: pd.DataFrame,
        rule: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate a single rule and check how well the generated data follows it."""
        target = rule.get("target")
        sources = rule.get("sources", [])

        rows_validated = 0
        rows_passed = 0
        violations = []

        for idx, row in df.iterrows():
            row_context = row.to_dict()

            # Skip if target is null
            if pd.isna(row.get(target)):
                continue

            rows_validated += 1

            try:
                # Generate expected value using the rule
                expected_value = SemanticRuleEngine.apply_rule(rule, row_context)
                actual_value = row.get(target)

                # Compare values (handling None/NaN)
                if expected_value is None and pd.isna(actual_value):
                    rows_passed += 1
                elif expected_value is not None and actual_value is not None:
                    # String comparison with normalization
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
            except Exception as e:
                violations.append(
                    {
                        "row_index": idx,
                        "error": str(e),
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
    def get_validation_flags(validation_report: Dict[str, Any]) -> Dict[str, bool]:
        """Return boolean flags for validation status."""
        return {
            "all_rules_passed": validation_report["rules_failed"] == 0,
            "high_quality": validation_report["validation_score"] >= 0.85,
            "acceptable_quality": validation_report["validation_score"] >= 0.7,
            "low_quality": validation_report["validation_score"] < 0.7,
            "any_violations": len(validation_report["violations"]) > 0,
        }
