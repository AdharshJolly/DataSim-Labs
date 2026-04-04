"""Identity-focused realism rule handlers."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Protocol

import pandas as pd

logger = logging.getLogger(__name__)

MALE_ALIASES = frozenset({"male", "m", "man", "männlich", "masculino"})
FEMALE_ALIASES = frozenset({"female", "f", "woman", "weiblich", "femenino"})


class _IdentityProcessorLike(Protocol):
    faker: Any
    rng: Any


def apply_name_gender_alignment(
    processor: _IdentityProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    name_col = rule["name_column"]
    gender_col = rule["gender_column"]

    if name_col not in df.columns or gender_col not in df.columns:
        logger.warning(
            "name_gender_alignment: column '%s' or '%s' not in DataFrame - skipping",
            name_col,
            gender_col,
        )
        return 0

    gender_norm = df[gender_col].astype(str).str.lower().str.strip()

    def pick_name(row_gender: str) -> str | None:
        if row_gender in MALE_ALIASES:
            return processor.faker.name_male()
        if row_gender in FEMALE_ALIASES:
            return processor.faker.name_female()
        return None

    updates = 0
    non_null_mask = df[gender_col].notna()
    for idx in df[non_null_mask].index:
        new_name = pick_name(gender_norm.at[idx])
        if new_name is not None:
            df.at[idx, name_col] = new_name
            updates += 1
    return updates


def apply_name_email_alignment(
    processor: _IdentityProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    name_col = rule["name_column"]
    email_col = rule["email_column"]

    if name_col not in df.columns or email_col not in df.columns:
        logger.warning(
            "name_email_alignment: column '%s' or '%s' not in DataFrame - skipping",
            name_col,
            email_col,
        )
        return 0

    def normalize(value: str) -> str:
        ascii_val = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
            .lower()
        )
        return re.sub(r"[^a-z0-9]+", "", ascii_val)

    def name_tokens(full_name: str) -> list[str]:
        parts = re.findall(r"[A-Za-z]+", full_name)
        return [normalize(part) for part in parts if len(part) >= 2]

    def build_local_part(first: str, last: str) -> str:
        first_part = normalize(first) or "user"
        last_part = normalize(last) or "profile"
        idx = int(processor.rng.integers(0, 5))
        if idx == 0:
            return f"{first_part}.{last_part}"
        if idx == 1:
            return f"{first_part}{last_part}"
        if idx == 2:
            return f"{first_part[0]}_{last_part}"
        if idx == 3:
            return f"{first_part}_{last_part[0]}"
        return f"{last_part}.{first_part}"

    updates = 0
    both_present = df[name_col].notna() & df[email_col].notna()

    for row_idx in df[both_present].index:
        name_val = str(df.at[row_idx, name_col])
        email_val = str(df.at[row_idx, email_col])

        if "@" not in email_val:
            continue

        local_part, domain = email_val.rsplit("@", 1)
        tokens = name_tokens(name_val)
        local_lower = local_part.lower()
        if any(token in local_lower for token in tokens if token):
            continue

        parts = re.findall(r"[A-Za-z]+", name_val)
        first = parts[0] if parts else "user"
        last = parts[-1] if len(parts) > 1 else "profile"
        new_local = build_local_part(first, last)
        df.at[row_idx, email_col] = f"{new_local}@{domain}"
        updates += 1

    return updates
