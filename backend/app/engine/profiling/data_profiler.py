import pandas as pd
from typing import Any, Dict, List
import numpy as np
import warnings

from app.engine.profiling.distribution_learner import DistributionLearner
from app.engine.profiling.correlation_engine import CorrelationEngine
from app.engine.semantic_rule_inference import infer_semantic_rules


SEMANTIC_UNIQUE_RATIO_THRESHOLD = 0.95


class DataProfiler:
    def __init__(self):
        self.distribution_learner = DistributionLearner()
        self.correlation_engine = CorrelationEngine()

    def profile_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Profile a complete dataset to learn distributions and correlations."""
        # Clean dataframe
        df = self._clean_dataframe(df)

        # 1. Detect columns and types
        column_profiles = {}
        for col in df.columns:
            column_profiles[col] = self._profile_column(df[col])

        # 2. Learn Correlations and Dependencies
        correlation_results = self.correlation_engine.compute_dependencies(
            df, column_profiles
        )

        # 3. Infer Semantic Rules using Gemini
        rule_inference_result = infer_semantic_rules(df)
        semantic_rules = rule_inference_result.get("rules", [])

        row_count = len(df)
        confidence_score = min(1.0, row_count / 200.0) if row_count > 0 else 0.0
        semantic_groups = self._detect_semantic_groups(list(df.columns))

        return {
            "columns": column_profiles,
            "dependency_graph": correlation_results.get("dependencies", []),
            "correlation_matrices": correlation_results.get("correlation_matrices", {}),
            "semantic_groups": semantic_groups,
            "semantic_rules": semantic_rules,
            "row_count": row_count,
            "metadata": {
                "row_count": row_count,
                "confidence_score": round(confidence_score, 3),
                "low_confidence": row_count < 50,
                "rule_inference_metadata": rule_inference_result.get("metadata", {}),
            },
        }

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values and basic cleanup."""
        # Replace empty strings with NaN
        df = df.replace(r"^\s*$", np.nan, regex=True)
        return df

    def _profile_column(self, series: pd.Series) -> Dict[str, Any]:
        """Detect type and learn distribution for a single column."""
        null_count = series.isna().sum()
        null_percentage = (null_count / len(series)) * 100 if len(series) > 0 else 0

        valid_series = series.dropna()
        unique_ratio = (
            float(valid_series.nunique() / len(valid_series))
            if len(valid_series) > 0
            else 0.0
        )
        semantic_type = self._detect_semantic_type(series.name)
        data_type = self._detect_data_type(valid_series, unique_ratio, semantic_type)

        # Learn distribution based on detected type
        distribution_profile = self.distribution_learner.learn_distribution(
            valid_series,
            data_type,
            column_name=series.name,
            semantic_type=semantic_type,
        )

        confidence = (
            0.95 if len(valid_series) >= 50 else max(0.2, len(valid_series) / 50.0)
        )

        return {
            "name": series.name,
            "data_type": data_type,
            "semantic_type": semantic_type if data_type == "semantic" else None,
            "unique_ratio": unique_ratio,
            "null_percentage": float(null_percentage),
            "distribution": distribution_profile,
            "confidence": round(float(confidence), 3),
        }

    def _detect_data_type(
        self, series: pd.Series, unique_ratio: float, semantic_type: str | None
    ) -> str:
        """Heuristic to detect data type."""
        if len(series) == 0:
            return "text"

        # Check if boolean
        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        # Check if numeric
        if pd.api.types.is_numeric_dtype(series):
            # Check if it's float or integer
            if pd.api.types.is_integer_dtype(series):
                # if there are only 2 values (0 and 1), might be boolean
                if set(series.unique()).issubset({0, 1}):
                    return "boolean"
                return "integer"
            else:
                return "float"

        # Check if date
        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"

        # Try to convert to datetime without noisy inference warnings.
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Could not infer format, so each element will be parsed individually",
                    category=UserWarning,
                )
                try:
                    parsed_dates = pd.to_datetime(
                        series,
                        errors="coerce",
                        format="mixed",
                    )
                except (TypeError, ValueError):
                    parsed_dates = pd.to_datetime(series, errors="coerce")

            parse_ratio = float(parsed_dates.notna().sum() / len(series))
            if parse_ratio >= 0.9:
                return "date"
        except (ValueError, TypeError):
            pass

        # Differentiate between categorical and text
        num_unique = series.nunique()
        total_valid = len(series)

        is_text_like = pd.api.types.is_string_dtype(series) or series.dtype == object
        if (
            semantic_type is not None
            and is_text_like
            and unique_ratio > SEMANTIC_UNIQUE_RATIO_THRESHOLD
        ):
            return "semantic"

        if num_unique < 20 or (num_unique / total_valid) < 0.1:
            return "categorical"

        return "text"

    def _detect_semantic_type(self, column_name: str | None) -> str | None:
        if not column_name:
            return None

        normalized = str(column_name).strip().lower()
        if "email" in normalized or normalized.endswith("mail"):
            return "email"
        if "address" in normalized or "addr" in normalized:
            return "address"
        if "name" in normalized:
            return "name"
        return None

    def _detect_semantic_groups(self, columns: List[str]) -> List[Dict[str, Any]]:
        """Detect common cross-column semantic groups for identity-linked generation."""
        normalized_to_original: Dict[str, str] = {
            str(column).strip().lower(): column for column in columns
        }

        groups: List[Dict[str, Any]] = []
        if all(
            key in normalized_to_original
            for key in ["first_name", "last_name", "email"]
        ):
            groups.append(
                {
                    "type": "identity",
                    "columns": [
                        normalized_to_original["first_name"],
                        normalized_to_original["last_name"],
                        normalized_to_original["email"],
                    ],
                }
            )

        if all(key in normalized_to_original for key in ["name", "email"]):
            email_column = normalized_to_original["email"]
            overlaps_existing = any(
                email_column in group.get("columns", []) for group in groups
            )
            if not overlaps_existing:
                groups.append(
                    {
                        "type": "identity",
                        "columns": [
                            normalized_to_original["name"],
                            email_column,
                        ],
                    }
                )

        return groups
