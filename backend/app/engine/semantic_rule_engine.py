"""Universal semantic rule engine for applying cross-column dependencies."""

import re
from typing import Any, Dict

import numpy as np


CONFIDENCE_THRESHOLD = 0.7
CONFIDENCE_STRICT_THRESHOLD = 0.85


class SemanticRuleEngine:
    """Applies semantic rules to generate dependent columns."""

    @staticmethod
    def apply_rule(rule: Dict[str, Any], row_context: Dict[str, Any]) -> Any:
        """Apply a single semantic rule to a row context."""
        transform = rule.get("transform", {})
        transform_type = transform.get("type", "").lower()

        if transform_type == "template":
            return SemanticRuleEngine._apply_template(rule, row_context)
        elif transform_type == "mapping":
            return SemanticRuleEngine._apply_mapping(rule, row_context)
        elif transform_type == "conditional":
            return SemanticRuleEngine._apply_conditional(rule, row_context)
        elif transform_type == "function":
            return SemanticRuleEngine._apply_function(rule, row_context)
        else:
            raise ValueError(f"Unknown transform type: {transform_type}")

    @staticmethod
    def _apply_template(rule: Dict[str, Any], row_context: Dict[str, Any]) -> str:
        """Apply template-based transformation (e.g., email: {first}.{last}@{domain})."""
        transform = rule.get("transform", {})
        template = transform.get("template", "")
        extractors = transform.get("extractors", {})
        domain_pool = transform.get("domain_pool", [])

        name_value = str(row_context.get("name", "") or "").strip()
        name_parts = [part for part in name_value.split() if part]
        default_first = name_parts[0].lower() if name_parts else "user"
        default_last = name_parts[-1].lower() if name_parts else "unknown"

        # Build context for template substitution
        context = {}
        for key, expr in extractors.items():
            try:
                context[key] = SemanticRuleEngine._evaluate_expression(
                    expr, row_context
                )
            except Exception:
                # If expression fails, skip this rule
                context[key] = ""

        if "first" not in context or not str(context.get("first", "")).strip():
            context["first"] = default_first
        if "last" not in context or not str(context.get("last", "")).strip():
            context["last"] = default_last

        # Add domain if available
        if domain_pool and "domain" not in context:
            rng = row_context.get("__rng__")
            if isinstance(rng, np.random.Generator):
                context["domain"] = str(rng.choice(domain_pool))
            else:
                context["domain"] = str(domain_pool[0])
        elif "domain" not in context:
            context["domain"] = "gmail.com"

        # Apply template
        try:
            if not template:
                return f"{context['first']}.{context['last']}@{context['domain']}"
            value = template.format(**context)
            constraints = rule.get("constraints", {})
            return SemanticRuleEngine._apply_constraints(value, constraints)
        except Exception:
            return None

    @staticmethod
    def _apply_mapping(rule: Dict[str, Any], row_context: Dict[str, Any]) -> Any:
        """Apply mapping-based transformation (e.g., city -> state)."""
        transform = rule.get("transform", {})
        mapping_table = transform.get("mapping_table", {})
        sources = rule.get("sources", [])

        if not sources or not mapping_table:
            return None

        # Get lookup key from first source column
        lookup_key_col = sources[0]
        if lookup_key_col not in row_context:
            return None

        lookup_key = row_context[lookup_key_col]
        mapped_value = mapping_table.get(str(lookup_key))

        if mapped_value is not None:
            constraints = rule.get("constraints", {})
            return SemanticRuleEngine._apply_constraints(mapped_value, constraints)

        return None

    @staticmethod
    def _apply_conditional(rule: Dict[str, Any], row_context: Dict[str, Any]) -> Any:
        """Apply conditional transformation (if-then logic)."""
        transform = rule.get("transform", {})
        conditions = transform.get("conditions", [])

        for condition in conditions:
            if_expr = condition.get("if", "")
            then_expr = condition.get("then", "")

            try:
                if SemanticRuleEngine._evaluate_condition(if_expr, row_context):
                    return SemanticRuleEngine._evaluate_expression(
                        then_expr, row_context
                    )
            except Exception:
                continue

        return None

    @staticmethod
    def _apply_function(rule: Dict[str, Any], row_context: Dict[str, Any]) -> Any:
        """Apply function-based transformation (e.g., uppercase, hash, etc.)."""
        transform = rule.get("transform", {})
        function_name = transform.get("function_name", "").lower()
        sources = rule.get("sources", [])

        if not sources:
            return None

        source_col = sources[0]
        if source_col not in row_context:
            return None

        value = row_context[source_col]

        try:
            if function_name == "uppercase":
                return str(value).upper()
            elif function_name == "lowercase":
                return str(value).lower()
            elif function_name == "capitalize":
                return str(value).capitalize()
            elif function_name == "reverse":
                return str(value)[::-1]
            elif function_name == "hash":
                import hashlib

                return hashlib.sha256(str(value).encode()).hexdigest()[:16]
            elif function_name == "prefix":
                prefix = transform.get("prefix", "")
                return f"{prefix}{value}"
            elif function_name == "suffix":
                suffix = transform.get("suffix", "")
                return f"{value}{suffix}"
        except Exception:
            return None

        return None

    @staticmethod
    def _evaluate_expression(expr: str, row_context: Dict[str, Any]) -> str:
        """Evaluate safe expressions like 'split(name)[0]' or column references."""
        expr = expr.strip()

        # Direct column reference
        if expr in row_context:
            val = row_context[expr]
            return str(val) if val is not None else ""

        # split(column)[index] pattern
        split_match = re.match(r"split\((\w+)\)\[(-?\d+)\]", expr)
        if split_match:
            col_name = split_match.group(1)
            index = int(split_match.group(2))
            if col_name in row_context:
                parts = str(row_context[col_name]).split()
                if -len(parts) <= index < len(parts):
                    return parts[index]
                return ""

        # lower(column) pattern
        lower_match = re.match(r"lower\((\w+)\)", expr)
        if lower_match:
            col_name = lower_match.group(1)
            if col_name in row_context:
                return str(row_context[col_name]).lower()

        # upper(column) pattern
        upper_match = re.match(r"upper\((\w+)\)", expr)
        if upper_match:
            col_name = upper_match.group(1)
            if col_name in row_context:
                return str(row_context[col_name]).upper()

        # substring(column, start, end) pattern
        substr_match = re.match(r"substring\((\w+),\s*(\d+),\s*(\d+)\)", expr)
        if substr_match:
            col_name = substr_match.group(1)
            start = int(substr_match.group(2))
            end = int(substr_match.group(3))
            if col_name in row_context:
                return str(row_context[col_name])[start:end]

        # prefix('value') pattern for literals
        prefix_match = re.match(r"prefix\(['\"]([^'\"]*)['\"]\)", expr)
        if prefix_match:
            return prefix_match.group(1)

        raise ValueError(f"Unknown expression: {expr}")

    @staticmethod
    def _evaluate_condition(condition: str, row_context: Dict[str, Any]) -> bool:
        """Evaluate safe conditions like 'country == "India"'."""
        condition = condition.strip()

        # Simple equality check: column == value
        eq_match = re.match(r"(\w+)\s*==\s*['\"]([^'\"]+)['\"]", condition)
        if eq_match:
            col_name = eq_match.group(1)
            expected_value = eq_match.group(2)
            if col_name in row_context:
                return str(row_context[col_name]) == expected_value
            return False

        # Inequality check: column != value
        neq_match = re.match(r"(\w+)\s*!=\s*['\"]([^'\"]+)['\"]", condition)
        if neq_match:
            col_name = neq_match.group(1)
            expected_value = neq_match.group(2)
            if col_name in row_context:
                return str(row_context[col_name]) != expected_value
            return False

        # IN check: column in [value1, value2]
        in_match = re.match(r"(\w+)\s+in\s+\[([^\]]+)\]", condition)
        if in_match:
            col_name = in_match.group(1)
            values_str = in_match.group(2)
            values = [v.strip().strip("\"'") for v in values_str.split(",")]
            if col_name in row_context:
                return str(row_context[col_name]) in values
            return False

        # Greater than check: column >= value (numeric)
        gte_match = re.match(r"(\w+)\s*>=\s*(\d+(?:\.\d+)?)", condition)
        if gte_match:
            col_name = gte_match.group(1)
            try:
                threshold = float(gte_match.group(2))
                if col_name in row_context:
                    val = row_context[col_name]
                    if isinstance(val, (int, float)):
                        return val >= threshold
                    try:
                        return float(val) >= threshold
                    except (ValueError, TypeError):
                        return False
            except (ValueError, TypeError):
                pass
            return False

        # Greater than check: column > value (numeric)
        gt_match = re.match(r"(\w+)\s*>\s*(\d+(?:\.\d+)?)", condition)
        if gt_match:
            col_name = gt_match.group(1)
            try:
                threshold = float(gt_match.group(2))
                if col_name in row_context:
                    val = row_context[col_name]
                    if isinstance(val, (int, float)):
                        return val > threshold
                    try:
                        return float(val) > threshold
                    except (ValueError, TypeError):
                        return False
            except (ValueError, TypeError):
                pass
            return False

        # Less than or equal check: column <= value (numeric)
        lte_match = re.match(r"(\w+)\s*<=\s*(\d+(?:\.\d+)?)", condition)
        if lte_match:
            col_name = lte_match.group(1)
            try:
                threshold = float(lte_match.group(2))
                if col_name in row_context:
                    val = row_context[col_name]
                    if isinstance(val, (int, float)):
                        return val <= threshold
                    try:
                        return float(val) <= threshold
                    except (ValueError, TypeError):
                        return False
            except (ValueError, TypeError):
                pass
            return False

        # Less than check: column < value (numeric)
        lt_match = re.match(r"(\w+)\s*<\s*(\d+(?:\.\d+)?)", condition)
        if lt_match:
            col_name = lt_match.group(1)
            try:
                threshold = float(lt_match.group(2))
                if col_name in row_context:
                    val = row_context[col_name]
                    if isinstance(val, (int, float)):
                        return val < threshold
                    try:
                        return float(val) < threshold
                    except (ValueError, TypeError):
                        return False
            except (ValueError, TypeError):
                pass
            return False

        raise ValueError(f"Unknown condition: {condition}")

    @staticmethod
    def _apply_constraints(value: str, constraints: Dict[str, Any]) -> str:
        """Apply string constraints (lowercase, no_spaces, etc.)."""
        if not value:
            return value

        if constraints.get("lowercase"):
            value = value.lower()
        if constraints.get("uppercase"):
            value = value.upper()
        if constraints.get("no_spaces"):
            value = value.replace(" ", "")
        if constraints.get("no_special_chars"):
            value = re.sub(r"[^\w]", "", value)
        if constraints.get("max_length"):
            max_len = constraints["max_length"]
            value = value[:max_len]

        return value


def filter_rules_by_confidence(
    rules: list[Dict[str, Any]], threshold: float = CONFIDENCE_THRESHOLD
) -> list[Dict[str, Any]]:
    """Filter rules by confidence threshold."""
    return [r for r in rules if r.get("confidence", 0) >= threshold]


def sort_rules_by_priority(rules: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Sort rules by priority (lower value = higher priority)."""
    return sorted(rules, key=lambda r: r.get("priority", 999))
