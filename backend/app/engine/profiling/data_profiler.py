import pandas as pd
from typing import Any, Dict, List
import numpy as np
import warnings
import re
from collections import Counter

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
        rule_inference_result = infer_semantic_rules(df, column_profiles)
        semantic_rules = rule_inference_result.get("rules", [])

        row_count = len(df)
        confidence_score = min(1.0, row_count / 200.0) if row_count > 0 else 0.0
        semantic_groups = self._detect_semantic_groups(df, column_profiles)

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
        if semantic_type is not None and is_text_like:
            return "semantic"

        if num_unique < 20 or (num_unique / total_valid) < 0.1:
            return "categorical"

        return "text"

    def _detect_semantic_type(self, column_name: str | None) -> str | None:
        if not column_name:
            return None

        normalized = re.sub(r"[^a-z0-9]+", "_", str(column_name).strip().lower())
        compact = normalized.replace("_", "")

        def has_any(patterns: List[str]) -> bool:
            return any(pattern in normalized or pattern in compact for pattern in patterns)

        if has_any(["email", "mail", "e_mail", "emailid"]):
            return "email"
        if has_any(
            [
                "fullname",
                "full_name",
                "display_name",
                "username",
                "user_name",
                "person_name",
                "employee_name",
                "name",
                "person",
                "employee",
            ]
        ):
            return "name"
        if has_any(["address", "addr", "street", "location"]):
            return "address"
        if has_any(["phone", "mobile", "cell", "tel"]):
            return "phone"
        if has_any(["url", "website", "web", "link"]):
            return "url"
        if has_any(
            [
                "company",
                "org",
                "organisation",
                "organization",
                "employer",
                "firm",
            ]
        ):
            return "company"
        if has_any(["city", "town", "municipality"]):
            return "city"
        if has_any(["country", "nation", "region"]):
            return "country"
        if has_any(["zip", "postal", "postcode", "pincode"]):
            return "zip"
        if has_any(["gender", "sex"]):
            return "gender"
        return None

    def _detect_semantic_groups(
        self,
        df: pd.DataFrame,
        column_profiles: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Detect semantic groups dynamically using inferred semantic types and observed data."""
        if df.empty:
            return []

        column_type_map: Dict[str, str] = {}
        for column in df.columns:
            inferred_type = None
            if column_profiles and column in column_profiles:
                inferred_type = column_profiles[column].get("semantic_type")
            if not inferred_type:
                inferred_type = self._detect_semantic_type(column)
            if inferred_type:
                column_type_map[str(column)] = inferred_type

        name_columns = [
            column for column, semantic_type in column_type_map.items() if semantic_type == "name"
        ]
        email_columns = [
            column for column, semantic_type in column_type_map.items() if semantic_type == "email"
        ]

        groups: List[Dict[str, Any]] = []
        if name_columns and email_columns:
            observed_domains, observed_domain_weights = self._extract_email_domains(
                df,
                email_columns,
            )
            identity_columns = [*name_columns, *email_columns]
            groups.append(
                {
                    "type": "identity",
                    "columns": identity_columns,
                    "column_type_map": {
                        column: column_type_map[column] for column in identity_columns
                    },
                    "observed_domains": observed_domains,
                    "observed_domain_weights": observed_domain_weights,
                }
            )

        return groups

    def _extract_email_domains(
        self,
        df: pd.DataFrame,
        email_columns: List[str],
    ) -> tuple[List[str], Dict[str, float]]:
        """Extract observed email domains and normalized frequency weights."""
        domain_counter: Counter[str] = Counter()
        pattern = re.compile(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})$")

        for column in email_columns:
            if column not in df.columns:
                continue
            for raw_value in df[column].dropna().astype(str):
                value = raw_value.strip().lower()
                match = pattern.search(value)
                if match:
                    domain_counter[match.group(1)] += 1

        if not domain_counter:
            return [], {}

        total = float(sum(domain_counter.values()))
        observed_domains = [domain for domain, _ in domain_counter.most_common()]
        observed_domain_weights = {
            domain: count / total for domain, count in domain_counter.items()
        }
        return observed_domains, observed_domain_weights
