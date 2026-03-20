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
        seed: int | None = None
    ) -> Dict[str, Any]:
        """Generate synthetic data from a saved profile."""
        manager = ProfileManager(db)
        profile = manager.get_profile_by_version(dataset_version_id)
        if not profile:
            raise ValueError("Profile not found for this dataset version.")

        generator = EnhancedDatasetGenerator(seed=seed)
        df = generator.generate_from_profile(profile=profile, row_count=row_count)

        # 4. Validate synthetic data against real profile
        from app.engine.profiling.validator import DataValidator
        validator = DataValidator()
        validation_report = validator.validate_synthetic_data(profile, df)

        return {
            "dataset_version_id": dataset_version_id,
            "rows": row_count,
            "data": df.to_dict(orient="records"),
            "validation_report": validation_report
        }
