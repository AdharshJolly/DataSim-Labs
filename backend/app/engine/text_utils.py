"""Shared text normalization utilities used across generators and realism handlers."""

from __future__ import annotations

import re
import unicodedata


def normalize_token(value: str) -> str:
    """Lowercase ASCII-only token from an arbitrary Unicode string."""
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "", ascii_value)


def split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first, last) tokens."""
    parts = re.findall(r"[A-Za-z]+", full_name)
    if not parts:
        return "user", "profile"
    if len(parts) == 1:
        return parts[0], "profile"
    return parts[0], parts[-1]
