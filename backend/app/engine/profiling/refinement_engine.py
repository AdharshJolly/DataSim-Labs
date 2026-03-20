import copy
import numpy as np
import pandas as pd
from typing import Dict, Any

from app.models.data_profile import DataProfile

class RefinementEngine:
    def __init__(self, learning_rate: float = 0.2):
        self.lr = learning_rate

    def refine_profile(
        self,
        current_profile: DataProfile,
        synthetic_df: pd.DataFrame,
        validation_report: Dict[str, Any]
    ) -> DataProfile:
        """Adjust distribution and correlation parameters based on validation errors."""
        new_columns = copy.deepcopy(current_profile.columns)
        new_correlation_matrices = copy.deepcopy(getattr(current_profile, 'correlation_matrices', {}))

        # 1. Refine Numeric and Categorical Column Distributions
        for col_name, metrics in validation_report.get("column_metrics", {}).items():
            if metrics.get("fidelity", 1.0) > 0.95:
                continue # Good enough

            prof = new_columns.get(col_name)
            if not prof:
                continue

            syn_series = synthetic_df[col_name].dropna()
            if len(syn_series) == 0:
                continue

            data_type = prof.get("data_type")
            dist = prof.get("distribution", {})

            if data_type in ["integer", "float"]:
                real_std = dist.get("std", 1.0) or 1.0
                syn_std = syn_series.std() or 0.0

                if syn_std < real_std:
                    dist["std"] = real_std * (1.0 + self.lr)
                elif syn_std > real_std:
                    dist["std"] = real_std * (1.0 - self.lr)

                if "quantiles" in dist:
                    real_mean = dist.get("mean", 0.0)
                    syn_mean = syn_series.mean()
                    mean_diff = real_mean - syn_mean
                    quantiles = np.array(dist["quantiles"])
                    quantiles += mean_diff * self.lr
                    dist["quantiles"] = quantiles.tolist()

            elif data_type in ["categorical", "boolean"]:
                real_cats = dist.get("categories", [])
                real_probs = dist.get("probabilities", [])
                if real_cats and real_probs:
                    syn_counts = syn_series.value_counts(normalize=True)
                    new_probs = []
                    for cat, real_prob in zip(real_cats, real_probs):
                        syn_prob = syn_counts.get(cat, 0.0)
                        error = real_prob - syn_prob
                        adjusted_prob = max(real_prob + (error * self.lr), 1e-6)
                        new_probs.append(adjusted_prob)

                    total_prob = sum(new_probs)
                    dist["probabilities"] = [p / total_prob for p in new_probs]

            new_columns[col_name]["distribution"] = dist

        # 2. Refine Correlation Matrices
        corr_error = validation_report.get("correlation_error")
        if corr_error is not None and corr_error > 0.05 and new_correlation_matrices:
            if "spearman" in new_correlation_matrices:
                cols = new_correlation_matrices.get("columns", [])
                cols = [c for c in cols if c in synthetic_df.columns]

                if len(cols) > 1:
                    real_corr = pd.DataFrame(new_correlation_matrices["spearman"]).loc[cols, cols].values
                    syn_corr = synthetic_df[cols].astype(float).corr(method='spearman').fillna(0).values

                    error_matrix = real_corr - syn_corr
                    adjusted_corr = real_corr + (error_matrix * self.lr)

                    np.fill_diagonal(adjusted_corr, 1.0)
                    adjusted_corr = np.clip(adjusted_corr, -1.0, 1.0)

                    adjusted_df = pd.DataFrame(adjusted_corr, index=cols, columns=cols)

                    orig_spearman_df = pd.DataFrame(new_correlation_matrices["spearman"])
                    orig_spearman_df.update(adjusted_df)
                    new_correlation_matrices["spearman"] = orig_spearman_df.to_dict()

        return DataProfile.new(
            dataset_version_id=current_profile.dataset_version_id,
            columns=new_columns,
            dependency_graph=copy.deepcopy(current_profile.dependency_graph),
            correlation_matrices=new_correlation_matrices,
            row_count=current_profile.row_count
        )
