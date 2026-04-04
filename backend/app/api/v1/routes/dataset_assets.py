"""Dataset assets route wrapper."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.dataset.assets import router as dataset_assets_router

router = APIRouter()
router.include_router(dataset_assets_router)
