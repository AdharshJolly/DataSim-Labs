import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any
from app.models.data_profile import DataProfile

class DataValidator:
    def validate_synthetic_data(self, real_profile: DataProfile, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
        """Compare synthetic data against the real data profile to calculate statistical fidelity."""
        report = {
            "overall_score": 0.0,
            "column_metrics": {},
            "correlation_error": None,
            "distribution_error": 0.0,
            "alerts": []
        }

        total_numeric_fidelity = 0.0
        numeric_count = 0

        total_categorical_fidelity = 0.0
        categorical_count = 0

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

            col_report = {
                "fidelity": 0.0,
                "null_pct_real": prof.get("null_percentage", 0.0),
                "null_pct_syn": (synthetic_df[col_name].isna().sum() / max(len(synthetic_df), 1)) * 100
            }

            fidelity_score = 1.0 # 0.0 to 1.0

            # 1. Numeric Validation (Mean diff, Std diff, KS Test)
            if data_type in ["integer", "float"] and len(syn_series) > 0:
                real_mean = real_dist.get("mean", 0.0)
                real_std = real_dist.get("std", 1.0) or 1.0

                syn_mean = syn_series.mean()
                syn_std = syn_series.std() or 0.0

                col_report["mean_diff"] = abs(syn_mean - real_mean)
                col_report["std_diff"] = abs(syn_std - real_std)

                mean_z_diff = abs(syn_mean - real_mean) / real_std
                std_z_diff = abs(syn_std - real_std) / real_std

                # KS Test (using quantiles to reconstruct real sample)
                if "quantiles" in real_dist:
                    quantiles = np.array(real_dist["quantiles"])
                    q_levels = np.linspace(0, 1, len(quantiles))

                    # Generate a representative sample of the real distribution
                    u_vals = np.linspace(0, 1, 1000)
                    real_sample = np.interp(u_vals, q_levels, quantiles)

                    # Calculate KS Statistic
                    ks_stat, p_value = stats.ks_2samp(syn_series, real_sample)
                    col_report["ks_statistic"] = ks_stat
                    col_report["ks_p_value"] = p_value

                    # KS statistic ranges from 0 to 1, where 0 is identical.
                    fidelity_score -= ks_stat
                else:
                    # Fallback if no quantiles available
                    fidelity_score -= min(mean_z_diff * 0.1 + std_z_diff * 0.1, 1.0)

                # Check null percentage drift
                null_drift = abs(col_report["null_pct_real"] - col_report["null_pct_syn"]) / 100.0
                fidelity_score -= null_drift

                fidelity_score = max(fidelity_score, 0.0)
                col_report["fidelity"] = fidelity_score
                report["column_metrics"][col_name] = col_report

                total_numeric_fidelity += fidelity_score
                numeric_count += 1

                if fidelity_score < 0.7:
                    report["alerts"].append({
                        "column": col_name,
                        "type": "distribution_drift",
                        "severity": "warning",
                        "message": f"Significant numeric drift detected (Fidelity: {fidelity_score*100:.1f}/100)."
                    })

            # 2. Categorical Validation (Frequency diff, KL Divergence)
            elif data_type in ["categorical", "boolean"] and len(syn_series) > 0:
                real_cats = real_dist.get("categories", [])
                real_probs = real_dist.get("probabilities", [])

                syn_counts = syn_series.value_counts(normalize=True)

                kl_divergence = 0.0
                tv_distance = 0.0 # Total Variation Distance

                for cat, real_prob in zip(real_cats, real_probs):
                    syn_prob = syn_counts.get(cat, 0.0)

                    # Total variation
                    tv_distance += abs(real_prob - syn_prob)

                    # KL Divergence
                    p = max(real_prob, 1e-9)
                    q = max(syn_prob, 1e-9)
                    kl_divergence += p * np.log(p / q)

                # TV Distance is divided by 2
                tv_distance = tv_distance / 2.0

                col_report["kl_divergence"] = kl_divergence
                col_report["tv_distance"] = tv_distance

                # Fidelity based on TV distance (0 is identical, 1 is completely disjoint)
                fidelity_score -= tv_distance

                # Check null percentage drift
                null_drift = abs(col_report["null_pct_real"] - col_report["null_pct_syn"]) / 100.0
                fidelity_score -= null_drift

                fidelity_score = max(fidelity_score, 0.0)
                col_report["fidelity"] = fidelity_score
                report["column_metrics"][col_name] = col_report

                total_categorical_fidelity += fidelity_score
                categorical_count += 1

                if fidelity_score < 0.7:
                    report["alerts"].append({
                        "column": col_name,
                        "type": "categorical_drift",
                        "severity": "warning",
                        "message": f"Significant categorical drift detected (Fidelity: {fidelity_score*100:.1f}/100)."
                    })
            else:
                col_report["fidelity"] = 1.0
                report["column_metrics"][col_name] = col_report

        numeric_score = (total_numeric_fidelity / numeric_count * 100) if numeric_count > 0 else 100.0
        categorical_score = (total_categorical_fidelity / categorical_count * 100) if categorical_count > 0 else 100.0

        # 3. Correlation Validation
        correlation_score = 100.0
        if hasattr(real_profile, 'correlation_matrices') and real_profile.correlation_matrices:
            corr_matrices = real_profile.correlation_matrices
            if "spearman" in corr_matrices:
                cols = corr_matrices.get("columns", [])
                cols = [c for c in cols if c in synthetic_df.columns]

                if len(cols) > 1:
                    real_corr = pd.DataFrame(corr_matrices["spearman"]).loc[cols, cols].values
                    syn_corr = synthetic_df[cols].astype(float).corr(method='spearman').fillna(0).values

                    # Frobenius Norm diff
                    frob_diff = np.linalg.norm(real_corr - syn_corr, 'fro')

                    # Mean Absolute Error of Correlation Matrix (upper triangle)
                    mask = np.triu(np.ones_like(real_corr, dtype=bool), k=1)
                    mae_corr = np.mean(np.abs(real_corr[mask] - syn_corr[mask]))

                    report["correlation_error"] = mae_corr

                    # Score drops by 10 points for every 0.1 of MAE
                    correlation_score = max(100.0 - (mae_corr * 100 * 2), 0.0)

                    if mae_corr > 0.15:
                        report["alerts"].append({
                            "type": "correlation_drift",
                            "severity": "warning",
                            "message": f"Global correlation deviates significantly (MAE: {mae_corr:.3f})."
                        })

        # Calculate final overall score
        # Weighted: Numeric (40%), Categorical (40%), Correlation (20%)
        weights = 0
        final_score = 0.0

        if numeric_count > 0:
            final_score += numeric_score * 0.4
            weights += 0.4

        if categorical_count > 0:
            final_score += categorical_score * 0.4
            weights += 0.4

        if report["correlation_error"] is not None:
            final_score += correlation_score * 0.2
            weights += 0.2

        if weights > 0:
            report["overall_score"] = final_score / weights
        else:
            report["overall_score"] = 100.0

        report["distribution_error"] = 100.0 - ((numeric_score + categorical_score) / 2)

        return report
