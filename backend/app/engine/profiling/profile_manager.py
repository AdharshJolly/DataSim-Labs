import uuid
from typing import Optional
from pymongo.database import Database

from app.models.data_profile import DataProfile

class ProfileManager:
    def __init__(self, db: Database):
        self.db = db
        self.collection = db["data_profiles"]

    def save_profile(self, dataset_version_id: uuid.UUID, profile_data: dict) -> DataProfile:
        """Save a new data profile for a specific dataset version."""
        data_profile = DataProfile.new(
            dataset_version_id=dataset_version_id,
            columns=profile_data.get("columns", {}),
            dependency_graph=profile_data.get("dependency_graph", []),
            correlation_matrices=profile_data.get("correlation_matrices", {}),
            row_count=profile_data.get("row_count", 0),
        )
        self.collection.insert_one(data_profile.to_document())
        return data_profile

    def get_profile_by_version(self, dataset_version_id: uuid.UUID) -> Optional[DataProfile]:
        """Retrieve a data profile by its associated dataset version ID."""
        document = self.collection.find_one({"dataset_version_id": str(dataset_version_id)})
        if document:
            return DataProfile.from_document(document)
        return None

    def delete_profile(self, profile_id: uuid.UUID) -> bool:
        """Delete a profile."""
        result = self.collection.delete_one({"_id": str(profile_id)})
        return result.deleted_count > 0
