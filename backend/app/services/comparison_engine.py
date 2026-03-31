"""Comparison engine for iterative refinement between expected and generated data."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engine.context.generation_context import GenerationContext


class ComparisonEngine:
    """Computes drift metrics and actionable refinement suggestions."""

    @staticmethod
    def compare(
        expected_df: pd.DataFrame | None = None,
        generated_df: pd.DataFrame | None = None,
        context: GenerationContext | None = None,
    ) -> dict[str, Any]:
        if context is not None:
            if expected_df is None:
                configured_expected = context.config.get("expected_df")
                if isinstance(configured_expected, pd.DataFrame):
                    expected_df = configured_expected
            if generated_df is None:
                configured_generated = context.config.get("generated_df")
                if isinstance(configured_generated, pd.DataFrame):
                    generated_df = configured_generated

        if expected_df is None or generated_df is None:
            raise ValueError("expected_df and generated_df are required for comparison")

        if expected_df.empty or generated_df.empty:
            return {
                "overall_drift_score": 0.0,
                "metrics": [],
                "recommendations": [],
            }

        shared_columns = [
            col for col in expected_df.columns if col in generated_df.columns
        ]

        metric_rows: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []
        drift_values: list[float] = []

        for column in shared_columns:
            expected_numeric = pd.to_numeric(
                expected_df[column], errors="coerce"
            ).dropna()
            generated_numeric = pd.to_numeric(
                generated_df[column], errors="coerce"
            ).dropna()

            if expected_numeric.empty or generated_numeric.empty:
                continue

            expected_mean = float(expected_numeric.mean())
            generated_mean = float(generated_numeric.mean())
            expected_var = (
                float(expected_numeric.var()) if len(expected_numeric) > 1 else 0.0
            )
            generated_var = (
                float(generated_numeric.var()) if len(generated_numeric) > 1 else 0.0
            )

            mean_diff = abs(generated_mean - expected_mean)
            variance_diff = abs(generated_var - expected_var)
            kl_divergence = ComparisonEngine._kl_divergence(
                expected_numeric, generated_numeric
            )

            metric_rows.append(
                {
                    "column": column,
                    "mean_diff": mean_diff,
                    "variance_diff": variance_diff,
                    "kl_divergence": kl_divergence,
                    "expected_mean": expected_mean,
                    "generated_mean": generated_mean,
                    "expected_variance": expected_var,
                    "generated_variance": generated_var,
                }
            )

            normalized_mean_drift = mean_diff / (abs(expected_mean) + 1.0)
            normalized_variance_drift = variance_diff / (abs(expected_var) + 1.0)
            combined_drift = (
                normalized_mean_drift + normalized_variance_drift + kl_divergence
            ) / 3.0
            drift_values.append(combined_drift)

            if combined_drift > 0.35:
                recommendations.append(
                    {
                        "attribute_name": column,
                        "action": "adjust_distribution",
                        "reason": "Detected high drift between expected and generated distribution.",
                        "suggested_distribution": (
                            "normal" if kl_divergence < 0.3 else "skewed"
                        ),
                        "confidence": min(0.95, 0.55 + combined_drift),
                    }
                )

        overall_drift_score = float(np.mean(drift_values)) if drift_values else 0.0

        return {
            "overall_drift_score": overall_drift_score,
            "metrics": metric_rows,
            "recommendations": recommendations,
        }

    @staticmethod
    def _kl_divergence(
        expected: pd.Series, generated: pd.Series, bins: int = 12
    ) -> float:
        min_val = min(float(expected.min()), float(generated.min()))
        max_val = max(float(expected.max()), float(generated.max()))
        if min_val == max_val:
            return 0.0

        hist_expected, edges = np.histogram(
            expected,
            bins=bins,
            range=(min_val, max_val),
            density=True,
        )
        hist_generated, _ = np.histogram(
            generated,
            bins=edges,
            density=True,
        )

        eps = 1e-9
        p = hist_expected + eps
        q = hist_generated + eps
        p = p / p.sum()
        q = q / q.sum()

        return float(np.sum(p * np.log(p / q)))
