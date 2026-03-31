"""Universal semantic rule engine for applying cross-column dependencies."""

import re
from collections import defaultdict, deque
from typing import Any, Dict

import numpy as np


CONFIDENCE_THRESHOLD = 0.7
CONFIDENCE_STRICT_THRESHOLD = 0.85
CONFLICT_POLICIES = {"priority_wins", "last_write_wins"}


def normalize_conflict_policy(conflict_policy: str | None) -> str:
    """Normalize the conflict resolution policy used for duplicate targets."""
    policy = str(conflict_policy or "priority_wins").strip().lower()
    return policy if policy in CONFLICT_POLICIES else "priority_wins"


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
    """Sort rules deterministically by priority, target, and id."""
    return sorted(
        rules,
        key=lambda r: (
            int(r.get("priority", 999)),
            str(r.get("target", "")),
            str(r.get("id", "")),
        ),
    )


def _validate_transform(rule: Dict[str, Any]) -> list[str]:
    errors: list[str] = []
    transform = rule.get("transform")
    if not isinstance(transform, dict):
        return ["transform must be an object"]

    transform_type = str(transform.get("type", "")).strip().lower()
    if transform_type not in {"template", "mapping", "conditional", "function"}:
        return [
            "transform.type must be one of: template, mapping, conditional, function"
        ]

    if transform_type == "template":
        template = transform.get("template")
        if template is not None and not isinstance(template, str):
            errors.append("template transform requires string 'template'")
        extractors = transform.get("extractors", {})
        if extractors is not None and not isinstance(extractors, dict):
            errors.append("template transform 'extractors' must be an object")
    elif transform_type == "mapping":
        mapping_table = transform.get("mapping_table")
        if not isinstance(mapping_table, dict) or not mapping_table:
            errors.append("mapping transform requires non-empty 'mapping_table' object")
    elif transform_type == "conditional":
        conditions = transform.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            errors.append("conditional transform requires non-empty 'conditions' array")
    elif transform_type == "function":
        function_name = transform.get("function_name")
        if not isinstance(function_name, str) or not function_name.strip():
            errors.append("function transform requires string 'function_name'")

    return errors


def _detect_rule_cycles(rules: list[Dict[str, Any]]) -> list[list[str]]:
    """Detect cycles among rule targets where sources reference other targets."""
    target_to_rule = {
        str(rule.get("target", "")).strip(): rule
        for rule in rules
        if str(rule.get("target", "")).strip()
    }

    graph: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {target: 0 for target in target_to_rule.keys()}

    for target, rule in target_to_rule.items():
        sources = rule.get("sources", []) or []
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            source_name = str(source).strip()
            if source_name in target_to_rule and source_name != target:
                if target not in graph[source_name]:
                    graph[source_name].add(target)
                    indegree[target] = indegree.get(target, 0) + 1

    queue = deque([node for node, degree in indegree.items() if degree == 0])
    visited_count = 0

    while queue:
        node = queue.popleft()
        visited_count += 1
        for neighbor in graph.get(node, set()):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if visited_count == len(indegree):
        return []

    cycle_nodes = [node for node, degree in indegree.items() if degree > 0]
    return [cycle_nodes] if cycle_nodes else []


def build_deterministic_execution_order(
    rules: list[Dict[str, Any]],
    conflict_policy: str = "priority_wins",
) -> list[Dict[str, Any]]:
    """Build a deterministic, dependency-aware execution order for valid rules."""
    if not rules:
        return []

    normalized_policy = normalize_conflict_policy(conflict_policy)
    sorted_rules = sort_rules_by_priority(rules)
    target_to_rule: dict[str, Dict[str, Any]] = {}
    for rule in sorted_rules:
        target = str(rule.get("target", "")).strip()
        if not target:
            continue
        if target not in target_to_rule:
            target_to_rule[target] = rule
            continue
        if normalized_policy == "last_write_wins":
            target_to_rule[target] = rule

    graph: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {target: 0 for target in target_to_rule.keys()}

    for target, rule in target_to_rule.items():
        sources = rule.get("sources", []) or []
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            source_name = str(source).strip()
            if source_name in target_to_rule and source_name != target:
                if target not in graph[source_name]:
                    graph[source_name].add(target)
                    indegree[target] += 1

    queue = deque(sorted([node for node, degree in indegree.items() if degree == 0]))
    ordered_targets: list[str] = []

    while queue:
        node = queue.popleft()
        ordered_targets.append(node)
        for neighbor in sorted(graph.get(node, set())):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    # Fallback for any unresolved nodes (should be prevented by cycle validation).
    if len(ordered_targets) < len(target_to_rule):
        unresolved = sorted(
            [
                target
                for target in target_to_rule.keys()
                if target not in ordered_targets
            ]
        )
        ordered_targets.extend(unresolved)

    return [
        target_to_rule[target] for target in ordered_targets if target in target_to_rule
    ]


def validate_semantic_rules(
    rules: list[Dict[str, Any]],
    available_columns: list[str] | None = None,
    conflict_policy: str = "priority_wins",
) -> dict[str, Any]:
    """Validate semantic rules and return sanitized output with diagnostics."""
    errors: list[str] = []
    warnings: list[str] = []
    sanitized: list[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    normalized_policy = normalize_conflict_policy(conflict_policy)
    available_set = {
        str(column).strip()
        for column in (available_columns or [])
        if str(column).strip()
    }

    for idx, raw_rule in enumerate(rules):
        rule = dict(raw_rule)
        prefix = f"rule[{idx}]"

        rule_id = str(rule.get("id", "")).strip()
        if not rule_id:
            errors.append(f"{prefix}: id is required")
            continue
        if rule_id in seen_ids:
            errors.append(f"{prefix}: duplicate id '{rule_id}'")
            continue
        seen_ids.add(rule_id)

        target = str(rule.get("target", "")).strip()
        if not target:
            errors.append(f"{prefix}: target is required")
            continue

        sources = rule.get("sources", [])
        if isinstance(sources, str):
            sources = [sources]
        if not isinstance(sources, list) or not sources:
            errors.append(f"{prefix}: sources must be a non-empty array")
            continue

        normalized_sources = [
            str(source).strip() for source in sources if str(source).strip()
        ]
        if not normalized_sources:
            errors.append(
                f"{prefix}: sources must contain at least one non-empty value"
            )
            continue

        if any(source == target for source in normalized_sources):
            errors.append(
                f"{prefix}: self-reference is not allowed (source == target '{target}')"
            )
            continue

        confidence = rule.get("confidence", CONFIDENCE_THRESHOLD)
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            errors.append(f"{prefix}: confidence must be a number")
            continue
        if confidence < 0 or confidence > 1:
            errors.append(f"{prefix}: confidence must be between 0 and 1")
            continue

        priority = rule.get("priority", 1)
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            errors.append(f"{prefix}: priority must be an integer")
            continue

        transform_errors = _validate_transform(rule)
        if transform_errors:
            errors.extend([f"{prefix}: {message}" for message in transform_errors])
            continue

        if available_set:
            unknown_columns = [
                col for col in [target, *normalized_sources] if col not in available_set
            ]
            if unknown_columns:
                errors.append(
                    f"{prefix}: unknown columns referenced: {', '.join(sorted(set(unknown_columns)))}"
                )
                continue

        sanitized.append(
            {
                **rule,
                "id": rule_id,
                "target": target,
                "sources": normalized_sources,
                "confidence": confidence,
                "priority": priority,
            }
        )

    target_counts: dict[str, int] = defaultdict(int)
    target_rules: dict[str, list[Dict[str, Any]]] = defaultdict(list)
    for rule in sanitized:
        target = str(rule.get("target", ""))
        target_counts[target] += 1
        target_rules[target].append(rule)
    conflict_targets = sorted(
        [target for target, count in target_counts.items() if count > 1]
    )
    conflict_resolution: dict[str, Any] = {}
    if conflict_targets:
        kept_rule_ids: dict[str, str] = {}
        dropped_rule_ids: dict[str, list[str]] = {}
        for target in conflict_targets:
            candidates = sort_rules_by_priority(target_rules[target])
            if normalized_policy == "last_write_wins":
                winner = candidates[-1]
            else:
                winner = candidates[0]
            winner_id = str(winner.get("id", ""))
            kept_rule_ids[target] = winner_id
            dropped_rule_ids[target] = [
                str(rule.get("id", ""))
                for rule in candidates
                if str(rule.get("id", "")) != winner_id
            ]
        conflict_resolution = {
            "policy": normalized_policy,
            "kept_rule_ids": kept_rule_ids,
            "dropped_rule_ids": dropped_rule_ids,
        }
        warnings.append(
            "Multiple rules write to the same target column(s): "
            + ", ".join(conflict_targets)
            + ". Conflict policy: "
            + normalized_policy
            + "."
        )

    cycles = _detect_rule_cycles(sanitized)
    if cycles:
        for cycle in cycles:
            errors.append(
                "Cyclic semantic rule dependency detected: " + " -> ".join(cycle)
            )

    ordered_rules = build_deterministic_execution_order(
        sanitized, conflict_policy=normalized_policy
    )
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "conflict_policy": normalized_policy,
        "conflict_resolution": conflict_resolution,
        "sanitized_rules": sanitized,
        "ordered_rules": ordered_rules,
    }
