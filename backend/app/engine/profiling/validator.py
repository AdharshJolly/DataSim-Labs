import pandas as pd
import numpy as np
from typing import Dict, Any
from app.models.data_profile import DataProfile

class DataValidator:
    def validate_synthetic_data(self, real_profile: DataProfile, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
        """Compare synthetic data against the real data profile to calculate drift."""
        report = {
            "drift_score": 0.0,
            "column_metrics": {},
            "alerts": []
        }

        total_drift = 0.0
        cols_checked = 0

        for col_name, prof in real_profile.columns.items():
            if col_name not in synthetic_df.columns:
                report["alerts"].append({
                    "column": col_name,
                    "type": "missing_column",
                    "severity": "high",
                    "message": f"Column {col_name} is missing in synthetic dataset."
                })
                continue

            syn_series = synthetic_df[col_name].dropna()
            real_dist = prof.get("distribution", {})
            data_type = prof.get("data_type")

            drift = 0.0

            # Check numeric drift (Difference in means relative to std dev)
            if data_type in ["integer", "float"] and len(syn_series) > 0:
                real_mean = real_dist.get("mean", 0.0)
                real_std = real_dist.get("std", 1.0)
                if real_std == 0:
                    real_std = 1.0

                syn_mean = syn_series.mean()
                syn_std = syn_series.std()

                # Z-score of the difference in means
                mean_drift = abs(syn_mean - real_mean) / real_std
                drift += mean_drift

                if mean_drift > 0.5:
                    report["alerts"].append({
                        "column": col_name,
                        "type": "mean_drift",
                        "severity": "warning",
                        "message": f"Mean drift detected: {mean_drift:.2f} standard deviations."
                    })

            # Check categorical drift (Jensen-Shannon or absolute probability difference)
            elif data_type in ["categorical", "boolean"] and len(syn_series) > 0:
                real_cats = real_dist.get("categories", [])
                real_probs = real_dist.get("probabilities", [])

                syn_counts = syn_series.value_counts(normalize=True)

                cat_drift = 0.0
                for cat, prob in zip(real_cats, real_probs):
                    syn_prob = syn_counts.get(cat, 0.0)
                    cat_drift += abs(prob - syn_prob)

                drift += cat_drift

                if cat_drift > 0.3:
                    report["alerts"].append({
                        "column": col_name,
                        "type": "category_distribution_drift",
                        "severity": "warning",
                        "message": f"Categorical distribution drift detected: {cat_drift:.2f} total variation."
                    })

            # Check null percentage drift
            real_null_pct = prof.get("null_percentage", 0.0)
            syn_null_pct = (synthetic_df[col_name].isna().sum() / len(synthetic_df)) * 100

            null_drift = abs(real_null_pct - syn_null_pct)
            if null_drift > 5.0:
                report["alerts"].append({
                    "column": col_name,
                    "type": "null_percentage_drift",
                    "severity": "warning",
                    "message": f"Null percentage drift detected: {null_drift:.2f}%."
                })

            report["column_metrics"][col_name] = {
                "drift": drift,
                "null_pct_real": real_null_pct,
                "null_pct_syn": syn_null_pct
            }

            total_drift += drift
            cols_checked += 1

        if cols_checked > 0:
            report["drift_score"] = total_drift / cols_checked

        return report
