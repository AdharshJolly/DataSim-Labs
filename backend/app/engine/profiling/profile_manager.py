import uuid
from typing import Optional
from pymongo.database import Database

from app.models.data_profile import DataProfile


class ProfileManager:
    def __init__(self, db: Database):
        self.db = db
        self.collection = db["data_profiles"]

    def save_profile(
        self, dataset_version_id: uuid.UUID, profile_data: dict
    ) -> DataProfile:
        """Save a new data profile for a specific dataset version."""
        row_count = int(profile_data.get("row_count", 0))
        confidence_score = min(1.0, row_count / 200.0) if row_count > 0 else 0.0
        low_confidence = row_count < 50

        metadata = dict(profile_data.get("metadata", {}))
        metadata.update(
            {
                "row_count": row_count,
                "confidence_score": round(confidence_score, 3),
                "low_confidence": low_confidence,
            }
        )

        data_profile = DataProfile.new(
            dataset_version_id=dataset_version_id,
            columns=profile_data.get("columns", {}),
            dependency_graph=profile_data.get("dependency_graph", []),
            correlation_matrices=profile_data.get("correlation_matrices", {}),
            semantic_groups=profile_data.get("semantic_groups", []),
            semantic_rules=profile_data.get("semantic_rules", []),
            row_count=row_count,
            metadata=metadata,
        )
        self.collection.insert_one(data_profile.to_document())
        return data_profile

    def get_profile_by_version(
        self, dataset_version_id: uuid.UUID
    ) -> Optional[DataProfile]:
        """Retrieve a data profile by its associated dataset version ID."""
        document = self.collection.find_one(
            {"dataset_version_id": str(dataset_version_id)}
        )
        if document:
            return DataProfile.from_document(document)
        return None

    def delete_profile(self, profile_id: uuid.UUID) -> bool:
        """Delete a profile."""
        result = self.collection.delete_one({"_id": str(profile_id)})
        return result.deleted_count > 0
