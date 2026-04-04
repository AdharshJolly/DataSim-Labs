"""Universal semantic rule engine for applying cross-column dependencies."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any

from app.engine.context.generation_context import GenerationContext
from app.engine.rules.transforms.conditional_transform import apply_conditional
from app.engine.rules.transforms.function_transform import apply_function
from app.engine.rules.transforms.mapping_transform import apply_mapping
from app.engine.rules.transforms.template_transform import apply_template


CONFIDENCE_THRESHOLD = 0.7
CONFIDENCE_STRICT_THRESHOLD = 0.85
CONFLICT_POLICIES = {"priority_wins", "last_write_wins"}


def normalize_conflict_policy(conflict_policy: str | None) -> str:
    """Normalize the conflict resolution policy used for duplicate targets."""
    policy = str(conflict_policy or "priority_wins").strip().lower()
    return policy if policy in CONFLICT_POLICIES else "priority_wins"


class SemanticRuleEngine:
    """Applies semantic rules to generate dependent columns."""

    _TRANSFORM_DISPATCH = {
        "template": apply_template,
        "mapping": apply_mapping,
        "conditional": apply_conditional,
        "function": apply_function,
    }

    @staticmethod
    def apply_rule(rule: dict[str, Any], row_context: dict[str, Any]) -> Any:
        """Apply a single semantic rule to a row context."""
        transform_type = rule.get("transform", {}).get("type", "").lower()
        handler = SemanticRuleEngine._TRANSFORM_DISPATCH.get(transform_type)
        if handler is None:
            raise ValueError(f"Unknown transform type: {transform_type}")
        value = handler(rule, row_context)
        constraints = rule.get("constraints", {})
        return SemanticRuleEngine._apply_constraints(value, constraints)

    @staticmethod
    def _apply_constraints(value: str, constraints: dict[str, Any]) -> str:
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
    rules: list[dict[str, Any]] | None = None,
    threshold: float = CONFIDENCE_THRESHOLD,
    context: GenerationContext | None = None,
) -> list[dict[str, Any]]:
    """Filter rules by confidence threshold."""
    resolved_rules = rules or []
    resolved_threshold = threshold

    if context is not None:
        if not resolved_rules:
            resolved_rules = context.semantic_rules

        threshold_from_context = context.config.get("semantic_confidence_threshold")
        if threshold_from_context is not None:
            try:
                resolved_threshold = float(threshold_from_context)
            except (ValueError, TypeError):
                resolved_threshold = threshold

    return [r for r in resolved_rules if r.get("confidence", 0) >= resolved_threshold]


def sort_rules_by_priority(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort rules deterministically by priority, target, and id."""
    return sorted(
        rules,
        key=lambda r: (
            int(r.get("priority", 999)),
            str(r.get("target", "")),
            str(r.get("id", "")),
        ),
    )


def _validate_transform(rule: dict[str, Any]) -> list[str]:
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


def _detect_rule_cycles(rules: list[dict[str, Any]]) -> list[list[str]]:
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
    rules: list[dict[str, Any]],
    conflict_policy: str = "priority_wins",
) -> list[dict[str, Any]]:
    """Build a deterministic, dependency-aware execution order for valid rules."""
    if not rules:
        return []

    normalized_policy = normalize_conflict_policy(conflict_policy)
    sorted_rules = sort_rules_by_priority(rules)
    target_to_rule: dict[str, dict[str, Any]] = {}
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
    rules: list[dict[str, Any]],
    available_columns: list[str] | None = None,
    conflict_policy: str = "priority_wins",
) -> dict[str, Any]:
    """Validate semantic rules and return sanitized output with diagnostics."""
    errors: list[str] = []
    warnings: list[str] = []
    sanitized: list[dict[str, Any]] = []
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
    target_rules: dict[str, list[dict[str, Any]]] = defaultdict(list)
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
