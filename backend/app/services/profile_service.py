import uuid
from typing import Any, Dict

import pandas as pd
from fastapi import UploadFile
from pymongo.database import Database

from app.engine.enhanced_generator import EnhancedDatasetGenerator
from app.engine.profiling.data_profiler import DataProfiler
from app.engine.profiling.profile_manager import ProfileManager
from app.engine.profiling.refinement_engine import RefinementEngine
from app.engine.profiling.validator import StatisticalValidator


NUMERIC_SIMILARITY_WEIGHT = 0.6
CATEGORICAL_SIMILARITY_WEIGHT = 0.4
GOOD_SCORE_THRESHOLD = 0.85
ACCEPTABLE_SCORE_THRESHOLD = 0.65


class ProfileService:
    @staticmethod
    def process_and_save_profile(
        db: Database,
        dataset_version_id: uuid.UUID,
        file: UploadFile,
    ) -> Dict[str, Any]:
        """Process uploaded dataset, profile it, save profile, and return explainability payload."""
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".json"):
            df = pd.read_json(file.file)
        elif file.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file.file)
        else:
            raise ValueError(
                "Unsupported file format. Please upload CSV, JSON, or Excel."
            )

        profiler = DataProfiler()
        profile_data = profiler.profile_dataset(df)

        manager = ProfileManager(db)
        saved_profile = manager.save_profile(dataset_version_id, profile_data)

        explainability = ProfileService._build_explainability_payload(
            saved_profile.columns,
            saved_profile.dependency_graph,
            saved_profile.metadata,
            saved_profile.row_count,
        )

        return {
            "profile_id": saved_profile.id,
            "dataset_version_id": saved_profile.dataset_version_id,
            "columns": saved_profile.columns,
            "dependency_graph": saved_profile.dependency_graph,
            "correlation_matrices": saved_profile.correlation_matrices,
            "semantic_groups": saved_profile.semantic_groups,
            "semantic_rules": saved_profile.semantic_rules,
            "row_count": saved_profile.row_count,
            "metadata": saved_profile.metadata,
            "explainability": explainability,
        }

    @staticmethod
    def get_profile(db: Database, dataset_version_id: uuid.UUID) -> Dict[str, Any]:
        """Get saved profile and explainability payload for a dataset version."""
        manager = ProfileManager(db)
        profile = manager.get_profile_by_version(dataset_version_id)
        if not profile:
            raise ValueError("Profile not found for this dataset version.")

        explainability = ProfileService._build_explainability_payload(
            profile.columns,
            profile.dependency_graph,
            profile.metadata,
            profile.row_count,
        )

        return {
            "profile_id": profile.id,
            "dataset_version_id": profile.dataset_version_id,
            "columns": profile.columns,
            "dependency_graph": profile.dependency_graph,
            "correlation_matrices": profile.correlation_matrices,
            "semantic_groups": profile.semantic_groups,
            "semantic_rules": profile.semantic_rules,
            "row_count": profile.row_count,
            "metadata": profile.metadata,
            "explainability": explainability,
        }

    @staticmethod
    def generate_from_profile(
        db: Database,
        dataset_version_id: uuid.UUID,
        row_count: int,
        seed: int | None = None,
        enable_feedback_loop: bool = True,
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """Generate synthetic rows strictly from learned profile parameters and dependencies."""
        manager = ProfileManager(db)
        base_profile = manager.get_profile_by_version(dataset_version_id)
        if not base_profile:
            raise ValueError("Profile not found for this dataset version.")

        if not base_profile.columns:
            raise ValueError(
                "Saved profile has no columns and cannot be used for generation."
            )

        generator = EnhancedDatasetGenerator(seed=seed)
        validator = StatisticalValidator()

        used_profile = base_profile
        refinement_history: list[dict[str, Any]] = []

        if enable_feedback_loop:
            refinement_engine = RefinementEngine(learning_rate=0.2)
            refinement_result = refinement_engine.refine(
                profile=base_profile,
                row_count=min(2000, row_count),
                max_iterations=max_iterations,
                seed=seed,
            )
            used_profile = refinement_result["profile"]
            refinement_history = refinement_result.get("history", [])

        generated_df = generator.generate_from_profile(
            profile=used_profile, row_count=row_count
        )
        validation_report = validator.validate(
            generated_df=generated_df,
            column_profiles=base_profile.columns,
            correlation_target=base_profile.correlation_matrices,
        )
        validation_summary = ProfileService._build_generation_validation_summary(
            generated_df,
            base_profile.columns,
        )
        
        # Validate semantic rules
        semantic_validation_report = None
        if base_profile.semantic_rules:
            from app.engine.semantic_rule_validator import SemanticRuleValidator
            
            semantic_validator = SemanticRuleValidator()
            semantic_validation_report = semantic_validator.validate_rules(
                generated_df, base_profile.semantic_rules
            )

        # Build user-facing generation warnings.
        generation_warnings: list[str] = []
        profile_row_count = base_profile.row_count or 0
        if profile_row_count < 50:
            generation_warnings.append(
                f"Low sample size (N={profile_row_count}). Generation quality may be "
                "reduced. Upload 100+ rows for reliable profiles."
            )
        coherence = validation_report.get("coherence_checks", {})
        coherence_score = coherence.get("name_email_coherence_score")
        if coherence_score is not None and coherence_score < 0.5:
            generation_warnings.append(
                f"Low name-email coherence ({coherence_score:.0%}). "
                "Email addresses may not match person names."
            )

        return {
            "dataset_version_id": dataset_version_id,
            "rows": row_count,
            "data": generated_df.to_dict(orient="records"),
            "semantic_groups": base_profile.semantic_groups,
            "validation_summary": validation_summary,
            "generation_warnings": generation_warnings,
            "generation_metadata": {
                "used_profile_id": str(used_profile.id),
                "base_profile_id": str(base_profile.id),
                "feedback_loop_enabled": enable_feedback_loop,
                "max_iterations": max_iterations,
                "iterations_used": (
                    len(refinement_history) if enable_feedback_loop else 1
                ),
                "refinement_history": refinement_history,
                "seed": seed,
                "profile_row_count": base_profile.row_count,
                "profile_confidence_score": base_profile.metadata.get(
                    "confidence_score", 0.0
                ),
                "low_confidence": base_profile.metadata.get("low_confidence", False),
                "semantic_groups": base_profile.semantic_groups,
                "semantic_rules": base_profile.semantic_rules,
                "semantic_rules_count": len(base_profile.semantic_rules),
                "semantic_validation_report": semantic_validation_report,
                "validation_report": validation_report,
            },
            # Backward-compatible fields preserved for existing consumers.
            "validation_report": validation_report,
            "realism_score": validation_report.get("realism_score"),
            "refinement_iterations_used": (
                len(refinement_history) if enable_feedback_loop else 1
            ),
        }

    @staticmethod
    def _build_generation_validation_summary(
        generated_df: pd.DataFrame,
        column_profiles: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build compact generation validation summary for UI visibility and trust signals."""
        numeric_similarities: list[float] = []
        mean_differences: list[float] = []
        std_differences: list[float] = []

        categorical_similarities: list[float] = []
        categorical_differences: list[float] = []

        for column_name, profile in column_profiles.items():
            if column_name not in generated_df.columns:
                continue

            distribution = profile.get("distribution", {})
            data_type = profile.get("data_type")
            generated_series = generated_df[column_name].dropna()
            if generated_series.empty:
                continue

            if data_type in {"integer", "float"}:
                target_mean = distribution.get("mean")
                target_std = distribution.get("std")
                if target_mean is None or target_std is None:
                    continue

                generated_mean = float(generated_series.mean())
                generated_std = float(generated_series.std()) if len(generated_series) > 1 else 0.0

                mean_diff = abs(generated_mean - float(target_mean))
                std_diff = abs(generated_std - float(target_std))
                mean_differences.append(mean_diff)
                std_differences.append(std_diff)

                scale = max(abs(float(target_std)), 1e-6)
                # Normalize differences into [0,1] similarities for weighted score aggregation.
                mean_similarity = max(0.0, 1.0 - (mean_diff / (3.0 * scale)))
                std_similarity = max(0.0, 1.0 - (std_diff / (2.0 * scale)))
                numeric_similarities.append((mean_similarity + std_similarity) / 2.0)

            if data_type in {"categorical", "boolean"}:
                categories = distribution.get("categories", [])
                probabilities = distribution.get("probabilities", [])
                if not categories or not probabilities:
                    continue

                observed = generated_series.value_counts(normalize=True)
                l1_difference = 0.0
                for category, target_probability in zip(categories, probabilities):
                    observed_probability = float(observed.get(category, 0.0))
                    l1_difference += abs(float(target_probability) - observed_probability)

                categorical_differences.append(l1_difference)
                categorical_similarity = max(0.0, 1.0 - (l1_difference / 2.0))
                categorical_similarities.append(categorical_similarity)

        numeric_similarity = (
            float(sum(numeric_similarities) / len(numeric_similarities))
            if numeric_similarities
            else 0.0
        )
        categorical_similarity = (
            float(sum(categorical_similarities) / len(categorical_similarities))
            if categorical_similarities
            else 0.0
        )

        total_weight = 0.0
        weighted_sum = 0.0
        if numeric_similarities:
            weighted_sum += numeric_similarity * NUMERIC_SIMILARITY_WEIGHT
            total_weight += NUMERIC_SIMILARITY_WEIGHT
        if categorical_similarities:
            weighted_sum += categorical_similarity * CATEGORICAL_SIMILARITY_WEIGHT
            total_weight += CATEGORICAL_SIMILARITY_WEIGHT

        score = round(weighted_sum / total_weight, 3) if total_weight > 0 else 0.0
        if score >= GOOD_SCORE_THRESHOLD:
            status = "good"
        elif score >= ACCEPTABLE_SCORE_THRESHOLD:
            status = "acceptable"
        else:
            status = "poor"

        return {
            "score": score,
            "status": status,
            "mean_difference": round(
                float(sum(mean_differences) / len(mean_differences)),
                4,
            )
            if mean_differences
            else 0.0,
            "std_deviation_difference": round(
                float(sum(std_differences) / len(std_differences)),
                4,
            )
            if std_differences
            else 0.0,
            "categorical_distribution_difference": round(
                float(sum(categorical_differences) / len(categorical_differences)),
                4,
            )
            if categorical_differences
            else 0.0,
        }

    @staticmethod
    def _build_explainability_payload(
        columns: Dict[str, Any],
        dependency_graph: list[Dict[str, Any]],
        metadata: Dict[str, Any],
        row_count: int,
    ) -> Dict[str, Any]:
        explainable_columns: Dict[str, Any] = {}
        for name, profile in columns.items():
            distribution = profile.get("distribution", {})
            explainable_columns[name] = {
                "type": profile.get("data_type"),
                "distribution": distribution.get("type", "unknown"),
                "mean": distribution.get("mean"),
                "std": distribution.get("std"),
                "min": distribution.get("min"),
                "max": distribution.get("max"),
                "confidence": profile.get(
                    "confidence", metadata.get("confidence_score", 0.0)
                ),
            }

        confidence_score = float(metadata.get("confidence_score", 0.0))
        if confidence_score >= 0.85:
            confidence_label = "high"
        elif confidence_score >= 0.6:
            confidence_label = "medium"
        else:
            confidence_label = "low"

        return {
            "columns": explainable_columns,
            "correlations": dependency_graph,
            "meta": {
                "rows_analyzed": int(metadata.get("row_count", row_count)),
                "confidence": confidence_label,
                "confidence_score": round(confidence_score, 3),
                "low_confidence": bool(metadata.get("low_confidence", row_count < 50)),
            },
        }
