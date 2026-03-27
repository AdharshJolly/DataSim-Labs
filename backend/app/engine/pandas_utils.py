"""
pandas_utils.py

Common DataFrame manipulation utilities used across generators and processors.
Provides reusable patterns for mutation, filtering, and row-level operations.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd


def apply_row_mutation(
    df: pd.DataFrame,
    mask: pd.Series,
    column: str,
    mutation_fn: Callable[[dict[str, Any]], Any],
) -> int:
    """
    Apply a mutation function to rows matching a mask.

    Args:
        df: DataFrame to mutate in-place
        mask: Boolean Series indicating which rows to update
        column: Column name to update
        mutation_fn: Function that takes a row dict and returns the new value

    Returns:
        Number of rows updated
    """
    updates = 0
    for idx in df[mask].index:
        row_data = df.loc[idx].to_dict()
        new_value = mutation_fn(row_data)
        if new_value is not None:
            df.at[idx, column] = new_value
            updates += 1
    return updates


def apply_conditional_assignment(
    df: pd.DataFrame,
    condition_mask: pd.Series,
    column: str,
    value_when_true: Any,
    value_when_false: Any | None = None,
) -> int:
    """
    Assign values based on a condition mask.

    Args:
        df: DataFrame to mutate in-place
        condition_mask: Boolean Series for assignment condition
        column: Column to update
        value_when_true: Value for True condition
        value_when_false: Value for False condition (optional)

    Returns:
        Number of rows updated
    """
    df.loc[condition_mask, column] = value_when_true
    updated = int(condition_mask.sum())

    if value_when_false is not None:
        df.loc[~condition_mask, column] = value_when_false
        updated += int((~condition_mask).sum())

    return updated


def apply_row_context_mutation(
    df: pd.DataFrame,
    mutation_fn: Callable[[int, dict[str, Any]], Any | tuple[str, Any] | None],
    target_columns: list[str] | None = None,
) -> int:
    """
    Apply mutations to each row using full row context.

    Args:
        df: DataFrame to mutate in-place
        mutation_fn: Function taking (row_idx, row_dict) and returning:
                     - None (no update)
                     - (column_name, value) to update single column
                     - dict to apply multiple updates {column: value, ...}
        target_columns: Optional pre-declared columns (will be created if missing)

    Returns:
        Number of rows updated
    """
    if target_columns:
        for col in target_columns:
            if col not in df.columns:
                df[col] = None

    updates = 0
    for idx in df.index:
        row_context = df.loc[idx].to_dict()
        result = mutation_fn(idx, row_context)

        if result is None:
            continue

        if isinstance(result, dict):
            for col, val in result.items():
                df.at[idx, col] = val
            updates += 1
        elif isinstance(result, tuple) and len(result) == 2:
            col, val = result
            df.at[idx, col] = val
            updates += 1

    return updates


def mask_from_condition(
    df: pd.DataFrame,
    column: str,
    condition: str,
    threshold: Any,
) -> pd.Series:
    """
    Create a boolean mask from a comparison condition.

    Args:
        df: DataFrame
        column: Column to evaluate
        condition: One of: "gt", "lt", "eq", "gte", "lte", "in", "ne"
        threshold: Comparison value(s)

    Returns:
        Boolean Series mask
    """
    source = df[column]
    non_null = source.notna()

    if condition == "gt":
        return non_null & (source > threshold)
    elif condition == "lt":
        return non_null & (source < threshold)
    elif condition == "eq":
        return non_null & (source == threshold)
    elif condition == "gte":
        return non_null & (source >= threshold)
    elif condition == "lte":
        return non_null & (source <= threshold)
    elif condition == "ne":
        return non_null & (source != threshold)
    elif condition == "in":
        return non_null & source.isin(
            threshold if isinstance(threshold, list) else [threshold]
        )
    else:
        raise ValueError(f"Unknown condition: {condition}")


def safe_column_mutation(
    df: pd.DataFrame,
    column: str,
    mutation_fn: Callable[[Any], Any],
    mask: pd.Series | None = None,
) -> int:
    """
    Safely apply mutation to a column, handling NaN values.

    Args:
        df: DataFrame to mutate in-place
        column: Column to update
        mutation_fn: Function to apply to each value
        mask: Optional pre-filter mask (defaults to non-null values)

    Returns:
        Number of rows updated
    """
    if mask is None:
        mask = df[column].notna()

    updates = 0
    for idx in df[mask].index:
        try:
            original_val = df.at[idx, column]
            new_val = mutation_fn(original_val)
            if new_val is not None:
                df.at[idx, column] = new_val
                updates += 1
        except (ValueError, TypeError):
            # Skip rows where mutation fails silently
            continue

    return updates


def vectorized_assignment(
    df: pd.DataFrame,
    column: str,
    values: pd.Series,
) -> int:
    """
    Vectorized assignment (preferred over row-by-row when possible).

    Args:
        df: DataFrame to mutate in-place
        column: Column to update
        values: Series of values indexed by row indices

    Returns:
        Number of rows updated
    """
    mask = values.notna()
    df.loc[mask, column] = values[mask]
    return int(mask.sum())


def fill_missing_columns(
    df: pd.DataFrame,
    column_specs: dict[str, Any],
) -> None:
    """
    Ensure specified columns exist in DataFrame, filling missing ones with None.

    Args:
        df: DataFrame to update in-place
        column_specs: Dict of {column_name: dtype or default_value}
    """
    for col_name, spec in column_specs.items():
        if col_name not in df.columns:
            df[col_name] = None


def get_row_context(
    df: pd.DataFrame,
    row_idx: int,
    include_index: bool = False,
) -> dict[str, Any]:
    """
    Extract row data as a dictionary with optional processing.

    Args:
        df: DataFrame
        row_idx: Row index
        include_index: Include row index in context

    Returns:
        Row as dict with optional index
    """
    row_data = df.loc[row_idx].to_dict()
    if include_index:
        row_data["__index__"] = row_idx
    return row_data
