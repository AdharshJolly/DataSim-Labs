"""Feedback collection and summary service for adaptive learning loops."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from pymongo.database import Database


class FeedbackService:
    """Store and summarize user feedback for dataset generations."""

    COLLECTION = "dataset_feedback"

    @staticmethod
    def submit_feedback(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_version_id: uuid.UUID | None,
        rating: int,
        comment: str | None,
        generation_signature: str | None,
        config_snapshot: dict[str, Any] | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        payload = {
            "_id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "dataset_id": str(dataset_id),
            "dataset_version_id": (
                str(dataset_version_id) if dataset_version_id else None
            ),
            "rating": int(rating),
            "comment": (comment or "").strip() or None,
            "generation_signature": generation_signature,
            "config_snapshot": config_snapshot or {},
            "created_at": now,
        }
        db[FeedbackService.COLLECTION].insert_one(payload)
        return payload

    @staticmethod
    def summarize_feedback(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {"user_id": str(user_id)}
        if dataset_id is not None:
            query["dataset_id"] = str(dataset_id)

        rows = list(
            db[FeedbackService.COLLECTION]
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

        if not rows:
            return {
                "count": 0,
                "average_rating": None,
                "ratings": [],
                "recent": [],
            }

        ratings = [
            int(row.get("rating", 0)) for row in rows if row.get("rating") is not None
        ]
        average = round(sum(ratings) / len(ratings), 3) if ratings else None

        recent = []
        for row in rows[:10]:
            recent.append(
                {
                    "dataset_id": row.get("dataset_id"),
                    "dataset_version_id": row.get("dataset_version_id"),
                    "rating": row.get("rating"),
                    "comment": row.get("comment"),
                    "created_at": row.get("created_at"),
                }
            )

        return {
            "count": len(rows),
            "average_rating": average,
            "ratings": ratings,
            "recent": recent,
        }
