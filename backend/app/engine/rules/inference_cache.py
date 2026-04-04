"""In-memory cache helpers for semantic rule inference."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

SEMANTIC_RULES_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL_SECONDS = 86400  # 24 hours


def compute_schema_hash(
    df: pd.DataFrame,
    column_metadata: dict[str, Any] | None = None,
) -> str:
    """Compute hash of dataset schema to use as cache key."""
    schema_info: dict[str, Any] = {
        "cols": sorted(df.columns.tolist()),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
    }
    if column_metadata:
        schema_info["metadata"] = {
            key: value.get("semantic_type", "")
            for key, value in column_metadata.items()
        }

    schema_json = json.dumps(schema_info, sort_keys=True)
    return hashlib.md5(schema_json.encode()).hexdigest()


def get_cached_rules(schema_hash: str) -> dict[str, Any] | None:
    """Retrieve rules from cache if valid."""
    if schema_hash not in SEMANTIC_RULES_CACHE:
        return None

    rules, timestamp = SEMANTIC_RULES_CACHE[schema_hash]
    age_seconds = datetime.now(timezone.utc).timestamp() - timestamp

    if age_seconds > CACHE_TTL_SECONDS:
        del SEMANTIC_RULES_CACHE[schema_hash]
        return None

    return rules


def cache_rules(schema_hash: str, rules: dict[str, Any]) -> None:
    """Store rules in cache."""
    SEMANTIC_RULES_CACHE[schema_hash] = (
        rules,
        datetime.now(timezone.utc).timestamp(),
    )
