"""Workflow orchestrator for preview generation."""

from __future__ import annotations

import uuid
from typing import Any

from pymongo.database import Database

from app.services.orchestration.generation_orchestrator import GenerationOrchestrator


class PreviewOrchestrator:
    """Handles only the preview workflow."""

    @staticmethod
    def run(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.generate_preview(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
            seed=seed,
        )
