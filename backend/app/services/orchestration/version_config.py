"""Resolve per-version realism/semantic config used in generation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.utils.rule_utils import validate_and_order_semantic_rules


@dataclass(slots=True)
class VersionGenerationConfig:
    """Normalized generation config resolved from stored version JSON."""

    realism_rules: list[dict[str, Any]]
    semantic_rules: list[dict[str, Any]]
    conflict_policy: str
    semantic_validation: dict[str, Any]


def resolve_version_generation_config(
    *,
    config_json: dict[str, Any],
    available_columns: list[str],
) -> VersionGenerationConfig:
    realism_config = config_json.get("realism")
    if isinstance(realism_config, dict) and isinstance(
        realism_config.get("rules"), list
    ):
        realism_rules = realism_config.get("rules", [])
    else:
        realism_rules = config_json.get("realism_rules", [])

    if not isinstance(realism_rules, list):
        realism_rules = []

    semantic_rules = config_json.get("semantic_rules", [])
    if not isinstance(semantic_rules, list):
        semantic_rules = []

    semantic_settings = config_json.get("semantic_rule_settings", {})
    conflict_policy_input = (
        (semantic_settings or {}).get("conflict_policy")
        if isinstance(semantic_settings, dict)
        else None
    )

    semantic_result = validate_and_order_semantic_rules(
        semantic_rules=semantic_rules,
        available_columns=available_columns,
        conflict_policy=conflict_policy_input,
    )

    return VersionGenerationConfig(
        realism_rules=realism_rules,
        semantic_rules=semantic_result["ordered_rules"],
        conflict_policy=semantic_result["conflict_policy"],
        semantic_validation=semantic_result["validation"],
    )
