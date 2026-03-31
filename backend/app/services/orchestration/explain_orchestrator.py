"""Workflow orchestrator for explain preview rows."""

from __future__ import annotations

import uuid
from typing import Any

from pymongo.database import Database

from app.services.generation_orchestrator import GenerationOrchestrator


class ExplainOrchestrator:
    """Handles only explain workflow for generated preview rows."""

    @staticmethod
    def run(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        row_index: int = 0,
        seed: int | None = None,
        column: str | None = None,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.explain_dataset_row(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
            row_index=row_index,
            seed=seed,
            column=column,
        )
