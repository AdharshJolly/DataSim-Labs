"""Dataset core route wrapper."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.dataset.core import router as dataset_core_router

router = APIRouter()
router.include_router(dataset_core_router)
