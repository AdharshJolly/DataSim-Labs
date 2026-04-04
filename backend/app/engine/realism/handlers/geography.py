"""Geography and locale realism rule handlers."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import pandas as pd

logger = logging.getLogger(__name__)


class _GeographyProcessorLike(Protocol):
    def _postal_for_country(self, normalized_country: str) -> str: ...

    def _phone_for_country(self, normalized_country: str) -> str: ...

    def _country_to_iban_code(self, normalized_country: str) -> str | None: ...

    def _generate_country_iban(self, country_code: str) -> str: ...


def apply_country_state_alignment(df: pd.DataFrame, rule: dict[str, Any]) -> int:
    country_col = rule["country_column"]
    state_col = rule["state_column"]
    state_by_country = rule["state_by_country"]

    if country_col not in df.columns or state_col not in df.columns:
        logger.warning(
            "country_state_alignment: column '%s' or '%s' not in DataFrame - skipping",
            country_col,
            state_col,
        )
        return 0

    normalized_mapping: dict[str, list[str]] = {}
    for country, states in state_by_country.items():
        if not isinstance(country, str) or not isinstance(states, list):
            continue
        valid_states = [
            str(state) for state in states if isinstance(state, str) and state
        ]
        if valid_states:
            normalized_mapping[country.strip().lower()] = valid_states

    if not normalized_mapping:
        return 0

    updates = 0
    for idx in df.index:
        country = df.at[idx, country_col]
        state = df.at[idx, state_col]
        if pd.isna(country):
            continue

        allowed = normalized_mapping.get(str(country).strip().lower())
        if not allowed:
            continue

        allowed_lower = {item.lower() for item in allowed}
        state_text = "" if pd.isna(state) else str(state).strip().lower()
        if state_text not in allowed_lower:
            df.at[idx, state_col] = allowed[0]
            updates += 1

    return updates


def apply_country_postal_format(
    processor: _GeographyProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    country_col = rule["country_column"]
    postal_col = rule["postal_column"]

    if country_col not in df.columns or postal_col not in df.columns:
        logger.warning(
            "country_postal_format: column '%s' or '%s' not in DataFrame - skipping",
            country_col,
            postal_col,
        )
        return 0

    updates = 0
    for idx in df.index:
        country = df.at[idx, country_col]
        if pd.isna(country):
            continue
        normalized_country = str(country).strip().lower()
        current = (
            ""
            if pd.isna(df.at[idx, postal_col])
            else str(df.at[idx, postal_col]).strip()
        )
        replacement = processor._postal_for_country(normalized_country)

        if not replacement:
            continue
        if current != replacement:
            df.at[idx, postal_col] = replacement
            updates += 1

    return updates


def apply_phone_format_by_country(
    processor: _GeographyProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    country_col = rule["country_column"]
    phone_col = rule["phone_column"]

    if country_col not in df.columns or phone_col not in df.columns:
        logger.warning(
            "phone_format_by_country: column '%s' or '%s' not in DataFrame - skipping",
            country_col,
            phone_col,
        )
        return 0

    updates = 0
    for idx in df.index:
        country = df.at[idx, country_col]
        if pd.isna(country):
            continue

        phone_value = processor._phone_for_country(str(country).strip().lower())
        if not phone_value:
            continue
        if str(df.at[idx, phone_col]) != phone_value:
            df.at[idx, phone_col] = phone_value
            updates += 1

    return updates


def apply_iban_format(
    processor: _GeographyProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    country_col = rule["country_column"]
    iban_col = rule["iban_column"]

    if country_col not in df.columns or iban_col not in df.columns:
        logger.warning(
            "iban_format: column '%s' or '%s' not in DataFrame - skipping",
            country_col,
            iban_col,
        )
        return 0

    updates = 0
    for idx in df.index:
        country = df.at[idx, country_col]
        if pd.isna(country):
            continue

        country_code = processor._country_to_iban_code(str(country).strip().lower())
        if not country_code:
            continue

        iban_value = processor._generate_country_iban(country_code)
        if str(df.at[idx, iban_col]) != iban_value:
            df.at[idx, iban_col] = iban_value
            updates += 1

    return updates
