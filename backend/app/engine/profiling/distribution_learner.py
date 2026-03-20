import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any

class DistributionLearner:
    def learn_distribution(self, series: pd.Series, data_type: str) -> Dict[str, Any]:
        """Learn statistical distribution for a series based on its data type."""
        if data_type in ["integer", "float"]:
            return self._learn_numeric_distribution(series)
        elif data_type in ["categorical", "boolean"]:
            return self._learn_categorical_distribution(series)
        elif data_type == "date":
            return self._learn_date_distribution(series)
        elif data_type == "text":
            return self._learn_text_distribution(series)
        return {}

    def _learn_numeric_distribution(self, series: pd.Series) -> Dict[str, Any]:
        """Learn mean, std, min, max, skewness, and infer distribution type using histograms and quantiles."""
        if len(series) == 0:
            return {"type": "uniform", "min": 0.0, "max": 1.0, "mean": 0.5, "std": 0.0, "skewness": 0.0}

        profile = {
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "skewness": float(series.skew()) if len(series) > 2 else 0.0,
        }

        # Quantile extraction (from 0 to 1 with 0.01 step)
        valid_series = series.dropna()
        if len(valid_series) > 0:
            quantiles = np.linspace(0, 1, 101)
            quantile_values = np.quantile(valid_series, quantiles)
            profile["quantiles"] = quantile_values.tolist()

            # Histogram-based distribution learning
            try:
                counts, bin_edges = np.histogram(valid_series, bins='auto')
                if len(counts) > 100:
                    counts, bin_edges = np.histogram(valid_series, bins=100)

                probabilities = counts / counts.sum()
                profile["histogram"] = {
                    "counts": counts.tolist(),
                    "probabilities": probabilities.tolist(),
                    "bin_edges": bin_edges.tolist()
                }
            except Exception:
                pass

        # Infer distribution type (normal, uniform, skewed, histogram)
        if len(valid_series) >= 8:
            if profile["max"] > profile["min"]:
                _, p_uniform = stats.kstest(valid_series, 'uniform', args=(profile["min"], profile["max"] - profile["min"]))
            else:
                p_uniform = 0.0

            sample = valid_series if len(valid_series) <= 5000 else valid_series.sample(5000)
            try:
                _, p_normal = stats.shapiro(sample)
            except ValueError:
                p_normal = 0.0

            if abs(profile["skewness"]) > 1.0:
                profile["type"] = "skewed"
                profile["skew_direction"] = "right" if profile["skewness"] > 0 else "left"
            elif p_normal > 0.05:
                profile["type"] = "normal"
            elif p_uniform > 0.05:
                profile["type"] = "uniform"
            else:
                profile["type"] = "histogram"

            from scipy.stats import norm, expon, gamma
            # Note: kstest requires scipy's internal distribution string names.
            # "exponential" is NOT valid — scipy uses "expon".
            distributions_to_try = [
                ("norm",  norm),
                ("gamma", gamma),
                ("expon", expon),
            ]
            # Human-readable names for storage (separate from scipy string names)
            dist_display_names = {"norm": "normal", "gamma": "gamma", "expon": "exponential"}

            fit_results = {}
            for dist_key, dist_obj in distributions_to_try:
                try:
                    params = dist_obj.fit(valid_series)
                    ks_stat, ks_p = stats.kstest(valid_series, dist_key, args=params)
                    fit_results[dist_key] = {"params": list(params), "ks_p": float(ks_p)}
                except Exception:
                    pass

            # Choose best fit (highest ks_p)
            if fit_results:
                best_key = max(fit_results, key=lambda d: fit_results[d]["ks_p"])
                profile["best_fit"] = dist_display_names.get(best_key, best_key)  # human name
                profile["best_fit_scipy_key"] = best_key                          # scipy name for kstest
                profile["fit_params"] = fit_results[best_key]["params"]
                profile["fit_ks_p"] = fit_results[best_key]["ks_p"]
        else:
            profile["type"] = "uniform"

        return profile

    def _learn_categorical_distribution(self, series: pd.Series) -> Dict[str, Any]:
        """Learn probabilities of each category."""
        if len(series) == 0:
            return {"type": "weighted_categorical", "categories": [], "probabilities": [], "unique_count": 0}

        value_counts = series.value_counts(normalize=True)
        return {
            "type": "weighted_categorical",
            "categories": value_counts.index.tolist(),
            "probabilities": value_counts.values.tolist(),
            "unique_count": len(value_counts)
        }

    def _learn_date_distribution(self, series: pd.Series) -> Dict[str, Any]:
        """Learn date range."""
        if len(series) == 0:
            return {}

        dates = pd.to_datetime(series, errors='coerce').dropna()
        if len(dates) == 0:
            return {}

        return {
            "min_date": dates.min().isoformat(),
            "max_date": dates.max().isoformat()
        }

    def _learn_text_distribution(self, series: pd.Series) -> Dict[str, Any]:
        """Text columns are mostly passed through Faker, but we can learn length stats."""
        if len(series) == 0:
            return {}

        lengths = series.astype(str).str.len()
        return {
            "min_length": float(lengths.min()),
            "max_length": float(lengths.max()),
            "mean_length": float(lengths.mean())
        }
