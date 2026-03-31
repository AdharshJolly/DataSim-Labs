"""Small response-building helpers for consistent API payload shape."""

from __future__ import annotations

from typing import Any


def build_preview_response(
    *,
    dataset_version_id: Any,
    data: list[dict[str, Any]],
    comparison: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "dataset_version_id": dataset_version_id,
        "rows": len(data),
        "data": data,
        "comparison": comparison,
    }


def build_generation_response(
    *,
    dataset_id: Any,
    row_count: int,
    generation_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "status": "completed",
        "row_count": row_count,
        "files": generation_result.get("files", []),
        "quality_report": generation_result.get("quality_report"),
        "quality_dashboard": generation_result.get("quality_dashboard"),
        "validation_summary": generation_result.get("validation_summary"),
        "quality_guardrails": generation_result.get("quality_guardrails"),
        "generation_signature": generation_result.get("generation_signature"),
        "generation_run_id": generation_result.get("generation_run_id"),
        "comparison": generation_result.get("comparison"),
        "semantic_rule_metrics": generation_result.get("semantic_rule_metrics"),
    }
