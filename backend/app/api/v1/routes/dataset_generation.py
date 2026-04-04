"""Dataset generation route wrapper."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.dataset.generation import router as dataset_generation_router

router = APIRouter()
router.include_router(dataset_generation_router)
