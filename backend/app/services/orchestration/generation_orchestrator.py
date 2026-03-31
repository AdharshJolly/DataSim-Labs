"""Workflow orchestrator for full dataset generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pymongo.database import Database

from app.services.generation_orchestrator import GenerationOrchestrator


class GenerationWorkflowOrchestrator:
    """Handles only full generation workflow."""

    @staticmethod
    def run(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        output_root: Path,
        chunk_size: int,
        seed: int | None = None,
        dataset_version_id: uuid.UUID | None = None,
        retention_hours: int = 24,
        enforce_sync_limits: bool = True,
    ) -> dict[str, Any]:
        return GenerationOrchestrator.generate_dataset_files(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            row_count=row_count,
            formats=formats,
            output_root=output_root,
            chunk_size=chunk_size,
            seed=seed,
            dataset_version_id=dataset_version_id,
            retention_hours=retention_hours,
            enforce_sync_limits=enforce_sync_limits,
        )
