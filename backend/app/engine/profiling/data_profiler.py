import pandas as pd
from typing import Any, Dict, List
import numpy as np

from app.engine.profiling.distribution_learner import DistributionLearner
from app.engine.profiling.correlation_engine import CorrelationEngine

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
        dependency_graph = self.correlation_engine.compute_dependencies(df, column_profiles)

        return {
            "columns": column_profiles,
            "dependency_graph": dependency_graph,
            "row_count": len(df)
        }

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values and basic cleanup."""
        # Replace empty strings with NaN
        df = df.replace(r'^\s*$', np.nan, regex=True)
        return df

    def _profile_column(self, series: pd.Series) -> Dict[str, Any]:
        """Detect type and learn distribution for a single column."""
        null_count = series.isna().sum()
        null_percentage = (null_count / len(series)) * 100 if len(series) > 0 else 0

        valid_series = series.dropna()
        data_type = self._detect_data_type(valid_series)

        # Learn distribution based on detected type
        distribution_profile = self.distribution_learner.learn_distribution(valid_series, data_type)

        return {
            "name": series.name,
            "data_type": data_type,
            "null_percentage": float(null_percentage),
            "distribution": distribution_profile
        }

    def _detect_data_type(self, series: pd.Series) -> str:
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

        # Try to convert to datetime
        try:
            pd.to_datetime(series, format=None, errors='raise')
            return "date"
        except (ValueError, TypeError):
            pass

        # Differentiate between categorical and text
        num_unique = series.nunique()
        total_valid = len(series)

        if num_unique < 20 or (num_unique / total_valid) < 0.1:
            return "categorical"

        return "text"
