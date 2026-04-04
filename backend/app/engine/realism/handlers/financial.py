"""Financial realism rule handlers."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import pandas as pd

logger = logging.getLogger(__name__)


class _FinancialProcessorLike(Protocol):
    def _generate_luhn_number(self, length: int = 16, prefix: str = "4") -> str: ...

    rng: Any


def apply_credit_card_luhn(
    processor: _FinancialProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    card_col = rule["card_column"]
    if card_col not in df.columns:
        logger.warning(
            "credit_card_luhn: column '%s' not in DataFrame - skipping", card_col
        )
        return 0

    length = max(12, min(19, int(rule.get("length", 16))))
    prefix = "".join(ch for ch in str(rule.get("prefix", "4")) if ch.isdigit())
    prefix = prefix or "4"

    updates = 0
    for idx in df.index:
        card_number = processor._generate_luhn_number(length=length, prefix=prefix)
        if str(df.at[idx, card_col]) != card_number:
            df.at[idx, card_col] = card_number
            updates += 1
    return updates


def apply_salary_band(
    processor: _FinancialProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    job_col = rule["job_column"]
    salary_col = rule["salary_column"]
    bands: dict[str, list[float]] = rule["bands"]

    if job_col not in df.columns or salary_col not in df.columns:
        logger.warning(
            "salary_band: column '%s' or '%s' not in DataFrame - skipping",
            job_col,
            salary_col,
        )
        return 0

    default_band = bands.get("default")

    updates = 0
    for idx in df.index:
        job_value = df.at[idx, job_col]
        if pd.isna(job_value):
            continue

        band = bands.get(str(job_value))
        if band is None:
            band = default_band
        if band is None:
            continue

        try:
            lo, hi = float(band[0]), float(band[1])
        except (IndexError, TypeError, ValueError):
            logger.warning(
                "salary_band: invalid band for job '%s' - skipping row", job_value
            )
            continue

        if lo > hi:
            lo, hi = hi, lo

        df.at[idx, salary_col] = round(float(processor.rng.uniform(lo, hi)), 2)
        updates += 1

    return updates
