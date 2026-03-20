import uuid
from typing import Any, Dict
import pandas as pd
from pymongo.database import Database
from fastapi import UploadFile

from app.engine.profiling.data_profiler import DataProfiler
from app.engine.profiling.profile_manager import ProfileManager
from app.engine.enhanced_generator import EnhancedDatasetGenerator

class ProfileService:
    @staticmethod
    def process_and_save_profile(
        db: Database,
        dataset_version_id: uuid.UUID,
        file: UploadFile
    ) -> Dict[str, Any]:
        """Process an uploaded dataset file, profile it, and save the profile."""
        # Read file into DataFrame
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        elif file.filename.endswith('.json'):
            df = pd.read_json(file.file)
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file.file)
        else:
            raise ValueError("Unsupported file format. Please upload CSV, JSON, or Excel.")

        # Profile dataset
        profiler = DataProfiler()
        profile_data = profiler.profile_dataset(df)

        # Save profile
        manager = ProfileManager(db)
        saved_profile = manager.save_profile(dataset_version_id, profile_data)

        return {
            "profile_id": saved_profile.id,
            "dataset_version_id": saved_profile.dataset_version_id,
            "columns": saved_profile.columns,
            "dependency_graph": saved_profile.dependency_graph,
            "row_count": saved_profile.row_count
        }

    @staticmethod
    def get_profile(db: Database, dataset_version_id: uuid.UUID) -> Dict[str, Any]:
        """Get the profile for a given dataset version."""
        manager = ProfileManager(db)
        profile = manager.get_profile_by_version(dataset_version_id)
        if not profile:
            raise ValueError("Profile not found for this dataset version.")

        return {
            "profile_id": profile.id,
            "dataset_version_id": profile.dataset_version_id,
            "columns": profile.columns,
            "dependency_graph": profile.dependency_graph,
            "row_count": profile.row_count
        }

    @staticmethod
    def generate_from_profile(
        db: Database,
        dataset_version_id: uuid.UUID,
        row_count: int,
        seed: int | None = None,
        enable_feedback_loop: bool = True,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """Generate synthetic data from a saved profile with an adaptive quality feedback loop."""
        manager = ProfileManager(db)
        original_profile = manager.get_profile_by_version(dataset_version_id)
        if not original_profile:
            raise ValueError("Profile not found for this dataset version.")

        from app.engine.profiling.validator import DataValidator
        from app.engine.profiling.refinement_engine import RefinementEngine
        validator = DataValidator()
        refinement_engine = RefinementEngine(learning_rate=0.2)

        best_df = None
        best_report = None
        best_score = -1.0

        current_profile = original_profile
        current_seed = seed

        attempts_used = 0

        # Quality Feedback Loop
        for attempt in range(1 if not enable_feedback_loop else max_iterations):
            attempts_used += 1
            generator = EnhancedDatasetGenerator(seed=current_seed)

            # For validation purposes, we can sample to improve performance if row_count is very large.
            # But since this returns the data, we must generate row_count.
            df = generator.generate_from_profile(profile=current_profile, row_count=row_count)

            validation_report = validator.validate_synthetic_data(original_profile, df)
            # overall_score is from 0 to 100
            fidelity_score = validation_report.get("overall_score", 0.0)

            if fidelity_score > best_score:
                best_score = fidelity_score
                best_df = df
                best_report = validation_report

            # If fidelity is excellent, we can stop early
            if best_score > 95.0:
                break

            if enable_feedback_loop and attempt < max_iterations - 1:
                # Mutate the seed
                if current_seed is not None:
                    current_seed += (attempt + 1) * 999

                # Apply Refinement Engine to adjust the profile parameters based on errors
                current_profile = refinement_engine.refine_profile(
                    current_profile,
                    best_df,
                    best_report
                )

        return {
            "dataset_version_id": dataset_version_id,
            "rows": row_count,
            "data": best_df.to_dict(orient="records"),
            "validation_report": best_report,
            "realism_score": best_score,
            "refinement_iterations_used": attempts_used
        }
