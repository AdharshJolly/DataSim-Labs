"""Workflow orchestrator for generation preflight checks."""

from __future__ import annotations

import uuid
from typing import Any

from pymongo.database import Database

from app.services.generation_orchestrator import GenerationOrchestrator


class PreflightOrchestrator:
    """Handles only preflight workflow."""

    @staticmethod
    def run(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        dataset_version_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.preflight_generation(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            row_count=row_count,
            formats=formats,
            dataset_version_id=dataset_version_id,
        )
