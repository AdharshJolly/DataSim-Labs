"""Semantic rules route wrapper."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.semantic.rules import router as semantic_rules_router

router = APIRouter()
router.include_router(semantic_rules_router)
