import copy
from typing import Any, Dict

import pandas as pd

from app.engine.enhanced_generator import EnhancedDatasetGenerator
from app.engine.profiling.validator import StatisticalValidator
from app.models.data_profile import DataProfile


class RefinementEngine:
    def __init__(self, learning_rate: float = 0.2) -> None:
        self.learning_rate = max(0.05, min(0.5, learning_rate))

    def refine(
        self,
        profile: DataProfile,
        row_count: int,
        max_iterations: int = 3,
        seed: int | None = None,
        drift_threshold: float = 0.15,
    ) -> Dict[str, Any]:
        """Run profile-guided refinement until drift is acceptable or max iterations are reached."""
        validator = StatisticalValidator()
        working_profile = copy.deepcopy(profile)

        history: list[dict[str, Any]] = []
        best_score = -1.0
        best_profile = working_profile
        best_report: Dict[str, Any] = {}
        previous_score: float | None = None

        for iteration in range(max_iterations):
            generator = EnhancedDatasetGenerator(
                seed=None if seed is None else seed + iteration
            )
            generated_df = generator.generate_from_profile(
                profile=working_profile,
                row_count=row_count,
            )

            report = validator.validate(
                generated_df=generated_df,
                column_profiles=working_profile.columns,
                correlation_target=working_profile.correlation_matrices,
            )

            score = float(report.get("score", 0.0))
            if score > best_score:
                best_score = score
                best_profile = copy.deepcopy(working_profile)
                best_report = report

            drift_metrics = self._compute_drift_metrics(report)
            max_drift = drift_metrics.get("max_drift", 0.0)
            improvement = (
                None if previous_score is None else round(score - previous_score, 4)
            )
            previous_score = score

            history.append(
                {
                    "iteration": iteration + 1,
                    "score": round(score, 4),
                    "status": report.get("status", "unknown"),
                    "max_drift": round(max_drift, 4),
                    "improvement": improvement,
                }
            )

            if max_drift <= drift_threshold and report.get("passed", False):
                break

            if iteration < max_iterations - 1:
                working_profile = self._refine_profile_parameters(
                    profile=working_profile,
                    report=report,
                    generated_df=generated_df,
                )

        return {
            "profile": best_profile,
            "validation_report": best_report,
            "history": history,
            "iterations_used": len(history),
        }

    def _compute_drift_metrics(self, report: Dict[str, Any]) -> Dict[str, float]:
        max_drift = 0.0

        for item in report.get("column_comparisons", {}).values():
            if item.get("type") == "numeric":
                max_drift = max(
                    max_drift,
                    float(item.get("mean_drift", 0.0)),
                    float(item.get("std_drift", 0.0)),
                )
            if item.get("type") == "categorical":
                max_drift = max(max_drift, float(item.get("l1_drift", 0.0)))

        corr_err = report.get("correlation_error", {})
        max_drift = max(max_drift, float(corr_err.get("max_pair_error", 0.0) or 0.0))

        return {"max_drift": max_drift}

    def _refine_profile_parameters(
        self,
        profile: DataProfile,
        report: Dict[str, Any],
        generated_df: pd.DataFrame,
    ) -> DataProfile:
        updated_columns = copy.deepcopy(profile.columns)

        for col_name, comparison in report.get("column_comparisons", {}).items():
            if col_name not in updated_columns:
                continue

            distribution = updated_columns[col_name].get("distribution", {})
            if not isinstance(distribution, dict):
                continue

            if comparison.get("type") == "numeric":
                target_mean = float(comparison.get("target_mean", 0.0))
                generated_mean = float(comparison.get("generated_mean", target_mean))
                target_std = float(comparison.get("target_std", 1.0) or 1.0)
                generated_std = float(comparison.get("generated_std", target_std))

                distribution["mean"] = target_mean + self.learning_rate * (
                    target_mean - generated_mean
                )
                distribution["std"] = max(
                    1e-6,
                    target_std + self.learning_rate * (target_std - generated_std),
                )

            if comparison.get("type") == "categorical":
                categories = distribution.get("categories", [])
                target_probs = distribution.get("probabilities", [])
                if categories and target_probs and col_name in generated_df.columns:
                    observed = generated_df[col_name].value_counts(normalize=True)
                    adjusted: list[float] = []
                    for category, current_prob in zip(categories, target_probs):
                        observed_prob = float(observed.get(category, 0.0))
                        adjusted_prob = float(current_prob) + self.learning_rate * (
                            float(current_prob) - observed_prob
                        )
                        adjusted.append(max(adjusted_prob, 1e-6))

                    total = sum(adjusted)
                    distribution["probabilities"] = [
                        value / total for value in adjusted
                    ]

        return DataProfile.new(
            dataset_version_id=profile.dataset_version_id,
            columns=updated_columns,
            dependency_graph=copy.deepcopy(profile.dependency_graph),
            correlation_matrices=copy.deepcopy(profile.correlation_matrices),
            semantic_groups=copy.deepcopy(profile.semantic_groups),
            semantic_rules=copy.deepcopy(profile.semantic_rules),
            row_count=profile.row_count,
            metadata=copy.deepcopy(profile.metadata),
        )
