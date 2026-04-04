from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.generation import GenerateResponse


class GenerationJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class GenerateAsyncResponse(BaseModel):
    job_id: str
    status: GenerationJobStatus
    message: str


class GenerationJobResponse(BaseModel):
    job_id: str
    dataset_id: UUID
    dataset_version_id: UUID | None
    status: GenerationJobStatus
    stage: str
    progress_percentage: int = Field(ge=0, le=100)
    row_count: int
    formats: list[str]
    seed: int | None = None
    cancel_requested: bool = False
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: GenerateResponse | None = None


class CancelGenerationJobResponse(BaseModel):
    job_id: str
    status: GenerationJobStatus
    cancel_requested: bool
    message: str


class GenerationJobListResponse(BaseModel):
    jobs: list[GenerationJobResponse]


class RetryGenerationJobResponse(BaseModel):
    original_job_id: str
    new_job_id: str
    status: GenerationJobStatus
    message: str
