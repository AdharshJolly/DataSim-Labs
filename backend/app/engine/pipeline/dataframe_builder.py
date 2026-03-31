"""Centralized DataFrame construction helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


class DataFrameBuilder:
    """Builds DataFrames from records or existing frame-like objects."""

    @staticmethod
    def from_records(records: list[dict[str, Any]] | None) -> pd.DataFrame:
        return pd.DataFrame(records or [])

    @staticmethod
    def ensure_dataframe(data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data
        if isinstance(data, list):
            return pd.DataFrame(data)
        if data is None:
            return pd.DataFrame()
        return pd.DataFrame(data)
