"""Conditional and temporal realism rule handlers."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def apply_age_gate(df: pd.DataFrame, rule: dict[str, Any]) -> int:
    age_col = rule["age_column"]
    target_col = rule["target_column"]
    minimum_age = int(rule["minimum_age"])
    override_value = rule["override_value"]

    if age_col not in df.columns or target_col not in df.columns:
        logger.warning(
            "age_gate: column '%s' or '%s' not in DataFrame - skipping",
            age_col,
            target_col,
        )
        return 0

    numeric_age = pd.to_numeric(df[age_col], errors="coerce")
    mask = numeric_age.notna() & (numeric_age < minimum_age)

    if mask.any():
        target_dtype = df[target_col].dtype
        typed_override: Any = override_value
        if pd.api.types.is_integer_dtype(target_dtype):
            try:
                typed_override = int(override_value)
            except (ValueError, TypeError):
                pass
        elif pd.api.types.is_float_dtype(target_dtype):
            try:
                typed_override = float(override_value)
            except (ValueError, TypeError):
                pass

        df.loc[mask, target_col] = typed_override
        return int(mask.sum())
    return 0


def apply_mutual_exclusion(df: pd.DataFrame, rule: dict[str, Any]) -> int:
    primary_col = rule["primary_column"]
    primary_values = rule["primary_values"]
    secondary_col = rule["secondary_column"]
    secondary_override = rule["secondary_override"]

    if primary_col not in df.columns or secondary_col not in df.columns:
        logger.warning(
            "mutual_exclusion: column '%s' or '%s' not in DataFrame - skipping",
            primary_col,
            secondary_col,
        )
        return 0

    threshold_values = (
        primary_values if isinstance(primary_values, list) else [primary_values]
    )
    lowered = {str(item).strip().lower() for item in threshold_values}
    mask = df[primary_col].astype(str).str.strip().str.lower().isin(lowered)
    if not mask.any():
        return 0

    df.loc[mask, secondary_col] = secondary_override
    return int(mask.sum())


def apply_conditional_value(df: pd.DataFrame, rule: dict[str, Any]) -> int:
    source_col = rule["source_column"]
    target_col = rule["target_column"]
    condition = rule["condition"]
    threshold = rule["threshold"]
    value_when_true = rule["value_when_true"]
    value_when_false = rule["value_when_false"]

    if source_col not in df.columns or target_col not in df.columns:
        logger.warning(
            "conditional_value: column '%s' or '%s' not in DataFrame - skipping",
            source_col,
            target_col,
        )
        return 0

    source = df[source_col]
    non_null = source.notna()

    if condition == "gt":
        mask = non_null & (source > threshold)
    elif condition == "lt":
        mask = non_null & (source < threshold)
    elif condition == "eq":
        mask = non_null & (source == threshold)
    elif condition == "gte":
        mask = non_null & (source >= threshold)
    elif condition == "lte":
        mask = non_null & (source <= threshold)
    elif condition == "in":
        if not isinstance(threshold, list):
            logger.warning(
                "conditional_value 'in' requires threshold to be a list - skipping"
            )
            return 0
        mask = non_null & source.isin(threshold)
    else:
        logger.warning(
            "conditional_value: unknown condition '%s' - skipping", condition
        )
        return 0

    df.loc[mask, target_col] = value_when_true
    df.loc[~mask & non_null, target_col] = value_when_false
    return int(non_null.sum())


def apply_date_relative_to(
    processor: Any, df: pd.DataFrame, rule: dict[str, Any]
) -> int:
    source_col = rule.get("source_column")
    target_col = rule.get("target_column")
    relation = str(rule.get("relation", "after")).strip().lower()

    if source_col not in df.columns or target_col not in df.columns:
        logger.warning(
            "date_relative_to: column '%s' or '%s' not in DataFrame - skipping",
            source_col,
            target_col,
        )
        return 0

    if relation not in {"after", "before", "same_day"}:
        logger.warning(
            "date_relative_to: unsupported relation '%s' - skipping", relation
        )
        return 0

    min_offset_days = max(0, int(rule.get("min_offset_days", 0)))
    max_offset_days = max(min_offset_days, int(rule.get("max_offset_days", 365)))

    source_series = pd.to_datetime(df[source_col], errors="coerce")
    target_series = pd.to_datetime(df[target_col], errors="coerce")

    updates = 0
    for idx in df.index:
        src_val = source_series.at[idx]
        tgt_val = target_series.at[idx]
        if pd.isna(src_val) or pd.isna(tgt_val):
            continue

        if relation == "same_day":
            if pd.Timestamp(tgt_val).date() != pd.Timestamp(src_val).date():
                df.at[idx, target_col] = pd.Timestamp(src_val).normalize()
                updates += 1
            continue

        random_offset_days = int(
            processor.rng.integers(min_offset_days, max_offset_days + 1)
        )
        offset = pd.Timedelta(days=random_offset_days)

        if relation == "after":
            min_allowed = pd.Timestamp(src_val) + pd.Timedelta(days=min_offset_days)
            max_allowed = pd.Timestamp(src_val) + pd.Timedelta(days=max_offset_days)
            if (
                pd.Timestamp(tgt_val) < min_allowed
                or pd.Timestamp(tgt_val) > max_allowed
            ):
                df.at[idx, target_col] = pd.Timestamp(src_val) + offset
                updates += 1
            continue

        min_allowed = pd.Timestamp(src_val) - pd.Timedelta(days=max_offset_days)
        max_allowed = pd.Timestamp(src_val) - pd.Timedelta(days=min_offset_days)
        if pd.Timestamp(tgt_val) < min_allowed or pd.Timestamp(tgt_val) > max_allowed:
            df.at[idx, target_col] = pd.Timestamp(src_val) - offset
            updates += 1

    return updates
