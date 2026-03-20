import pandas as pd
import numpy as np
from scipy.stats import ks_2samp, kstest, norm, expon, gamma
from typing import Dict, Any

class StatisticalValidator:
    def validate(
        self,
        generated_df: pd.DataFrame,
        column_profiles: Dict[str, Any],
        correlation_target: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:

        report: Dict[str, Any] = {
            "ks_tests": {},
            "kl_divergence": {},
            "correlation_error": {
                "frobenius_norm": None,
                "max_pair_error": None,
                "pairs_above_threshold": 0,
                "passed": True
            },
            "null_fidelity": {},
            "realism_score": 100,
            "confidence": "unknown",
            "warnings": [],
            "passed": False
        }

        # Validate we have profiles
        if not column_profiles:
            report["warnings"].append({
                "severity": "warning",
                "type": "no_profile",
                "column": None,
                "message": "No column profiles provided for validation."
            })
            report["realism_score"] = None  # type: ignore
            return report

        # Downsample if too large to keep under 2 seconds
        if len(generated_df) > 5000:
            sample_df = generated_df.sample(5000, random_state=42)
        else:
            sample_df = generated_df

        for col_name, prof in column_profiles.items():
            if col_name not in sample_df.columns:
                report["warnings"].append({
                    "severity": "error",
                    "type": "missing_column",
                    "column": col_name,
                    "message": f"Column {col_name} is missing in generated dataset."
                })
                continue

            syn_series = sample_df[col_name]
            valid_syn_series = syn_series.dropna()
            real_dist = prof.get("distribution", {})
            data_type = prof.get("data_type")

            # Null fidelity
            target_ratio = float(prof.get("null_percentage", 0.0) / 100.0)
            actual_ratio = float(syn_series.isna().sum() / max(len(syn_series), 1))
            drift = abs(target_ratio - actual_ratio)
            null_passed = drift <= 0.05

            report["null_fidelity"][col_name] = {
                "target_ratio": target_ratio,
                "actual_ratio": actual_ratio,
                "drift": drift,
                "passed": null_passed
            }
            if not null_passed:
                report["realism_score"] -= 3
                report["warnings"].append({
                    "severity": "warning",
                    "type": "null_fidelity",
                    "column": col_name,
                    "message": f"Null ratio drift of {drift:.3f} exceeds threshold."
                })

            if len(valid_syn_series) == 0:
                continue

            # Numeric KS Test
            if data_type in ["integer", "float"]:
                stat = 1.0
                p_val = 0.0

                # Check for reference sample from quantiles
                if "quantiles" in real_dist:
                    quantiles = np.array(real_dist["quantiles"])
                    q_levels = np.linspace(0, 1, len(quantiles))
                    u_vals = np.linspace(0, 1, max(len(valid_syn_series), 1000))
                    ref_sample = np.interp(u_vals, q_levels, quantiles)
                    stat, p_val = ks_2samp(valid_syn_series, ref_sample)
                elif "best_fit" in real_dist and "fit_params" in real_dist:
                    dist_name = real_dist.get("best_fit_scipy_key", real_dist.get("best_fit", "norm"))
                    params = real_dist["fit_params"]
                    if dist_name in ("normal", "norm"):
                        stat, p_val = kstest(valid_syn_series, 'norm', args=params)
                    elif dist_name == "gamma":
                        stat, p_val = kstest(valid_syn_series, 'gamma', args=params)
                    elif dist_name in ("exponential", "expon"):
                        stat, p_val = kstest(valid_syn_series, 'expon', args=params)
                else:
                    mean = real_dist.get("mean", 0.0)
                    std = real_dist.get("std", 1.0)
                    if std == 0: std = 1.0
                    stat, p_val = kstest(valid_syn_series, 'norm', args=(mean, std))

                passed = bool(p_val > 0.05)
                report["ks_tests"][col_name] = {
                    "statistic": float(stat),
                    "p_value": float(p_val),
                    "passed": passed,
                    "interpretation": f"Distribution matches target (p={p_val:.3f})" if passed else f"Distribution diverges (p={p_val:.3f})"
                }
                if not passed:
                    report["realism_score"] -= 5

            # Categorical KL Divergence
            elif data_type in ["categorical", "boolean"]:
                real_cats = real_dist.get("categories", [])
                real_probs = real_dist.get("probabilities", [])

                if real_cats and real_probs:
                    syn_counts = valid_syn_series.value_counts(normalize=True)

                    kl_div = 0.0
                    eps = 1e-10
                    for cat, prob in zip(real_cats, real_probs):
                        p = max(prob, eps)
                        q = max(syn_counts.get(cat, 0.0), eps)
                        kl_div += p * np.log(p / q)

                    passed = bool(kl_div < 0.1)
                    report["kl_divergence"][col_name] = {
                        "kl_div": float(kl_div),
                        "passed": passed,
                        "interpretation": f"Category distribution matches (KL={kl_div:.3f})" if passed else f"Category distribution diverges (KL={kl_div:.3f})"
                    }
                    if not passed:
                        report["realism_score"] -= 8

        # Correlation Error
        if correlation_target and "spearman" in correlation_target:
            cols = correlation_target.get("columns", [])
            cols = [c for c in cols if c in sample_df.columns]

            if len(cols) > 1:
                target_corr = pd.DataFrame(correlation_target["spearman"]).loc[cols, cols].values
                gen_corr = sample_df[cols].astype(float).corr(method='spearman').fillna(0).values

                frob_norm = float(np.linalg.norm(gen_corr - target_corr, 'fro'))

                mask = np.triu(np.ones_like(target_corr, dtype=bool), k=1)
                diffs = np.abs(target_corr[mask] - gen_corr[mask])
                max_error = float(np.max(diffs)) if len(diffs) > 0 else 0.0
                pairs_above = int(np.sum(diffs > 0.1))

                passed = bool(frob_norm <= 0.3)
                report["correlation_error"] = {
                    "frobenius_norm": frob_norm,
                    "max_pair_error": max_error,
                    "pairs_above_threshold": pairs_above,
                    "passed": passed
                }

                if not passed:
                    report["realism_score"] -= 10
                    report["warnings"].append({
                        "severity": "warning",
                        "type": "correlation_drift",
                        "column": None,
                        "message": f"Global correlation deviated (Frobenius norm = {frob_norm:.3f})"
                    })

        # Finalize scoring
        report["realism_score"] = max(min(report["realism_score"], 100), 0)

        if report["realism_score"] >= 85:
            report["confidence"] = "high"
        elif report["realism_score"] >= 60:
            report["confidence"] = "medium"
        else:
            report["confidence"] = "low"

        report["passed"] = bool(report["realism_score"] >= 75)

        return report
