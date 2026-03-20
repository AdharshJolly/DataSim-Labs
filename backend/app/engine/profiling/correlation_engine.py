import pandas as pd
import numpy as np
from typing import Dict, Any, List

class CorrelationEngine:
    def compute_dependencies(self, df: pd.DataFrame, column_profiles: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compute dependencies between columns to form a dependency graph."""
        dependencies = []

        # 1. Numeric Correlations
        numeric_cols = [col for col, prof in column_profiles.items() if prof["data_type"] in ["integer", "float"]]
        if len(numeric_cols) > 1:
            numeric_df = df[numeric_cols].dropna()
            if len(numeric_df) > 10:  # Need enough data
                # Convert explicitly to float to avoid issues with boolean or string representation
                try:
                    numeric_df = numeric_df.astype(float)
                    corr_matrix = numeric_df.corr(method='pearson')
                    for i in range(len(numeric_cols)):
                        for j in range(i + 1, len(numeric_cols)):
                            col1, col2 = numeric_cols[i], numeric_cols[j]
                            corr_val = corr_matrix.loc[col1, col2]
                            if pd.notna(corr_val) and abs(corr_val) > 0.5:  # Strong correlation threshold
                                dependencies.append({
                                    "source": col1,
                                    "target": col2,
                                    "type": "linear_correlation",
                                    "correlation": float(corr_val)
                                })
                except (ValueError, TypeError):
                    pass

        # 2. Categorical Conditional Dependencies
        categorical_cols = [col for col, prof in column_profiles.items() if prof["data_type"] == "categorical"]

        for cat_col in categorical_cols:
            for other_col in df.columns:
                if cat_col == other_col:
                    continue

                prof = column_profiles[other_col]

                # Check mapping from cat_col -> other_col
                # e.g. country -> state
                # If for a given value of cat_col, other_col has very low entropy, there's a dependency.
                if prof["data_type"] == "categorical":
                    mapping_dep = self._check_categorical_mapping(df, cat_col, other_col)
                    if mapping_dep:
                        dependencies.append(mapping_dep)
                elif prof["data_type"] in ["integer", "float"]:
                    # Conditional numeric distributions
                    cond_dep = self._check_conditional_numeric(df, cat_col, other_col)
                    if cond_dep:
                        dependencies.append(cond_dep)

        return dependencies

    def _check_categorical_mapping(self, df: pd.DataFrame, source: str, target: str) -> Dict[str, Any]:
        """Check if target strongly depends on source (e.g., country -> state)."""
        clean_df = df[[source, target]].dropna()
        if len(clean_df) < 10:
            return None

        # Group by source, check if target has 1 dominant value
        grouped = clean_df.groupby(source)[target]
        mapping = {}
        strong_mapping_count = 0

        for val, group in grouped:
            if len(group) < 3:
                continue
            top_val = group.value_counts(normalize=True).head(1)
            if not top_val.empty and top_val.iloc[0] > 0.8:  # 80% certainty
                mapping[str(val)] = {
                    "value": str(top_val.index[0]),
                    "probability": float(top_val.iloc[0])
                }
                strong_mapping_count += 1

        # If more than 50% of valid groups have a strong mapping, we record a dependency
        num_groups = len([g for g in grouped if len(g[1]) >= 3])
        if num_groups > 0 and (strong_mapping_count / num_groups) > 0.5:
            return {
                "source": source,
                "target": target,
                "type": "categorical_mapping",
                "mapping": mapping
            }
        return None

    def _check_conditional_numeric(self, df: pd.DataFrame, source: str, target: str) -> Dict[str, Any]:
        """Check if numeric target distribution changes based on categorical source."""
        clean_df = df[[source, target]].dropna()
        if len(clean_df) < 20:
            return None

        try:
            clean_df[target] = clean_df[target].astype(float)
        except (ValueError, TypeError):
            return None

        grouped = clean_df.groupby(source)[target]
        conditional_dists = {}

        overall_std = clean_df[target].std()
        if pd.isna(overall_std) or overall_std == 0:
            return None

        significant_diff = False
        overall_mean = clean_df[target].mean()

        for val, group in grouped:
            if len(group) < 5:
                continue
            group_mean = group.mean()
            group_std = group.std()

            # If group mean differs significantly from overall mean
            if abs(group_mean - overall_mean) > overall_std * 0.5:
                significant_diff = True

            conditional_dists[str(val)] = {
                "mean": float(group_mean),
                "std": float(group_std) if pd.notna(group_std) and len(group) > 1 and group_std > 0 else float(overall_std),
                "min": float(group.min()),
                "max": float(group.max())
            }

        if significant_diff and len(conditional_dists) > 0:
            return {
                "source": source,
                "target": target,
                "type": "conditional_numeric",
                "distributions": conditional_dists
            }

        return None
