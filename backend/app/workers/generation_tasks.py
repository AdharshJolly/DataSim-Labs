from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.dataset_service import DatasetService


def generate_dataset_job(
    *,
    user_id: str,
    dataset_id: str,
    dataset_version_id: str | None,
    row_count: int,
    formats: list[str],
) -> dict[str, object]:
    """Run dataset generation in a worker process and return serializable result."""
    db = SessionLocal()
    try:
        files = DatasetService.generate_dataset_files(
            db=db,
            user_id=UUID(user_id),
            dataset_id=UUID(dataset_id),
            dataset_version_id=UUID(dataset_version_id) if dataset_version_id else None,
            row_count=row_count,
            formats=formats,
            output_root=Path(settings.artifacts_dir),
            chunk_size=settings.generation_chunk_size,
            seed=None,
            retention_hours=settings.artifact_retention_hours,
        )
        return {
            "dataset_id": dataset_id,
            "status": "completed",
            "row_count": row_count,
            "files": files,
        }
    finally:
        db.close()
