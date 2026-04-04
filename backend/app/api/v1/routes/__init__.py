from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.dataset_assets import router as assets_router
from app.api.v1.routes.dataset_core import router as core_router
from app.api.v1.routes.dataset_generation import router as generation_router
from app.api.v1.routes.dataset_jobs import router as jobs_router

router = APIRouter()
router.include_router(core_router)
router.include_router(generation_router)
router.include_router(jobs_router)
router.include_router(assets_router)

__all__ = ["router"]
