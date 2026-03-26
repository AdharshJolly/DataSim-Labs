import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, kstest
from typing import Any, Dict


class StatisticalValidator:
    def validate(
        self,
        generated_df: pd.DataFrame,
        column_profiles: Dict[str, Any],
        correlation_target: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        sampled_rows = int(len(generated_df))
        low_confidence = sampled_rows < 50
        confidence_score = min(1.0, sampled_rows / 200.0) if sampled_rows > 0 else 0.0

        report: Dict[str, Any] = {
            "ks_tests": {},
            "kl_divergence": {},
            "column_comparisons": {},
            "correlation_error": {
                "frobenius_norm": None,
                "max_pair_error": None,
                "pairs_above_threshold": 0,
                "passed": True,
            },
            "null_fidelity": {},
            "realism_score": 100,
            "score": 1.0,
            "status": "excellent",
            "confidence": "unknown",
            "confidence_score": round(confidence_score, 3),
            "low_confidence": low_confidence,
            "rows_analyzed": sampled_rows,
            "warnings": [],
            "passed": False,
        }

        if not column_profiles:
            report["warnings"].append(
                {
                    "severity": "warning",
                    "type": "no_profile",
                    "column": None,
                    "message": "No column profiles provided for validation.",
                }
            )
            report["realism_score"] = None
            report["score"] = 0.0
            report["status"] = "insufficient"
            return report

        sample_df = (
            generated_df.sample(5000, random_state=42)
            if len(generated_df) > 5000
            else generated_df
        )

        for col_name, prof in column_profiles.items():
            if col_name not in sample_df.columns:
                report["warnings"].append(
                    {
                        "severity": "error",
                        "type": "missing_column",
                        "column": col_name,
                        "message": f"Column {col_name} is missing in generated dataset.",
                    }
                )
                continue

            syn_series = sample_df[col_name]
            valid_syn_series = syn_series.dropna()
            real_dist = prof.get("distribution", {})
            data_type = prof.get("data_type")

            target_ratio = float(prof.get("null_percentage", 0.0) / 100.0)
            actual_ratio = float(syn_series.isna().sum() / max(len(syn_series), 1))
            null_drift = abs(target_ratio - actual_ratio)
            null_passed = null_drift <= 0.05
            report["null_fidelity"][col_name] = {
                "target_ratio": target_ratio,
                "actual_ratio": actual_ratio,
                "drift": null_drift,
                "passed": null_passed,
            }
            if not null_passed:
                report["realism_score"] -= 3

            if len(valid_syn_series) == 0:
                continue

            if data_type in ["integer", "float"]:
                stat = 1.0
                p_val = 0.0

                if "quantiles" in real_dist:
                    quantiles = np.array(real_dist["quantiles"])
                    q_levels = np.linspace(0, 1, len(quantiles))
                    u_vals = np.linspace(0, 1, max(len(valid_syn_series), 1000))
                    ref_sample = np.interp(u_vals, q_levels, quantiles)
                    stat, p_val = ks_2samp(valid_syn_series, ref_sample)
                elif "best_fit" in real_dist and "fit_params" in real_dist:
                    dist_name = real_dist.get(
                        "best_fit_scipy_key", real_dist.get("best_fit", "norm")
                    )
                    params = real_dist["fit_params"]
                    if dist_name in ("normal", "norm"):
                        stat, p_val = kstest(valid_syn_series, "norm", args=params)
                    elif dist_name == "gamma":
                        stat, p_val = kstest(valid_syn_series, "gamma", args=params)
                    elif dist_name in ("exponential", "expon"):
                        stat, p_val = kstest(valid_syn_series, "expon", args=params)
                else:
                    mean = float(real_dist.get("mean", 0.0))
                    std = float(real_dist.get("std", 1.0)) or 1.0
                    stat, p_val = kstest(valid_syn_series, "norm", args=(mean, std))

                generated_mean = float(valid_syn_series.mean())
                generated_std = (
                    float(valid_syn_series.std()) if len(valid_syn_series) > 1 else 0.0
                )
                target_mean = float(real_dist.get("mean", generated_mean))
                target_std = float(real_dist.get("std", generated_std))

                mean_drift = abs(generated_mean - target_mean)
                std_drift = abs(generated_std - target_std)

                passed = bool(p_val > 0.05)
                report["ks_tests"][col_name] = {
                    "statistic": float(stat),
                    "p_value": float(p_val),
                    "passed": passed,
                    "interpretation": (
                        f"Distribution matches target (p={p_val:.3f})"
                        if passed
                        else f"Distribution diverges (p={p_val:.3f})"
                    ),
                }
                report["column_comparisons"][col_name] = {
                    "type": "numeric",
                    "target_mean": target_mean,
                    "generated_mean": generated_mean,
                    "mean_drift": mean_drift,
                    "target_std": target_std,
                    "generated_std": generated_std,
                    "std_drift": std_drift,
                }
                if not passed:
                    report["realism_score"] -= 5
                if mean_drift > max(0.1, abs(target_std) * 0.35):
                    report["realism_score"] -= 2
                if std_drift > max(0.1, abs(target_std) * 0.35):
                    report["realism_score"] -= 2

            elif data_type in ["categorical", "boolean", "semantic"]:
                real_cats = real_dist.get("categories", [])
                real_probs = real_dist.get("probabilities", [])

                if real_cats and real_probs:
                    syn_counts = valid_syn_series.value_counts(normalize=True)

                    kl_div = 0.0
                    eps = 1e-10
                    l1_drift = 0.0
                    for cat, prob in zip(real_cats, real_probs):
                        p = max(float(prob), eps)
                        q = max(float(syn_counts.get(cat, 0.0)), eps)
                        kl_div += p * np.log(p / q)
                        l1_drift += abs(p - q)

                    passed = bool(kl_div < 0.1)
                    report["kl_divergence"][col_name] = {
                        "kl_div": float(kl_div),
                        "passed": passed,
                        "interpretation": (
                            f"Category distribution matches (KL={kl_div:.3f})"
                            if passed
                            else f"Category distribution diverges (KL={kl_div:.3f})"
                        ),
                    }
                    report["column_comparisons"][col_name] = {
                        "type": "categorical",
                        "l1_drift": float(l1_drift),
                        "categories_compared": len(real_cats),
                    }
                    if not passed:
                        report["realism_score"] -= 8
                else:
                    # Semantic columns still contribute to confidence checks through null fidelity.
                    report["column_comparisons"][col_name] = {
                        "type": "semantic",
                        "note": "No categorical baseline available; validated via null and metadata checks.",
                    }

        if correlation_target and "spearman" in correlation_target:
            cols = [
                c
                for c in correlation_target.get("columns", [])
                if c in sample_df.columns
            ]
            if len(cols) > 1:
                target_corr = (
                    pd.DataFrame(correlation_target["spearman"]).loc[cols, cols].values
                )
                gen_corr = (
                    sample_df[cols]
                    .astype(float)
                    .corr(method="spearman")
                    .fillna(0)
                    .values
                )

                frob_norm = float(np.linalg.norm(gen_corr - target_corr, "fro"))
                mask = np.triu(np.ones_like(target_corr, dtype=bool), k=1)
                diffs = np.abs(target_corr[mask] - gen_corr[mask])
                max_error = float(np.max(diffs)) if len(diffs) > 0 else 0.0
                pairs_above = int(np.sum(diffs > 0.1))
                passed = bool(frob_norm <= 0.3)

                report["correlation_error"] = {
                    "frobenius_norm": frob_norm,
                    "max_pair_error": max_error,
                    "pairs_above_threshold": pairs_above,
                    "passed": passed,
                }
                if not passed:
                    report["realism_score"] -= 10

        report["realism_score"] = max(min(int(report["realism_score"]), 100), 0)
        report["score"] = round(report["realism_score"] / 100.0, 3)

        if report["realism_score"] >= 90:
            report["status"] = "excellent"
        elif report["realism_score"] >= 75:
            report["status"] = "good"
        elif report["realism_score"] >= 60:
            report["status"] = "fair"
        else:
            report["status"] = "poor"

        if report["realism_score"] >= 85:
            report["confidence"] = "high"
        elif report["realism_score"] >= 60:
            report["confidence"] = "medium"
        else:
            report["confidence"] = "low"

        report["passed"] = bool(report["realism_score"] >= 75)
        if low_confidence:
            report["warnings"].append(
                {
                    "severity": "warning",
                    "type": "low_sample_size",
                    "column": None,
                    "message": "Validation used fewer than 50 rows; confidence is reduced.",
                }
            )

        return report
