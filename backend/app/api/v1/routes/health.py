from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health check")
def health_check() -> dict[str, Any]:
    async_enabled = settings.async_generation_enabled
    worker_status = "disabled"
    worker_reason: str | None = None

    if async_enabled:
        state_file = _worker_state_file_path()
        if state_file.exists():
            payload = _read_worker_state_file(state_file)
            if payload.get("status") == "degraded":
                worker_status = "degraded"
                reason = payload.get("reason")
                worker_reason = str(reason) if reason else "unknown"
            else:
                worker_status = "enabled"
        else:
            worker_status = "enabled"

    response: dict[str, Any] = {
        "status": "ok",
        "async_generation_enabled": async_enabled,
        "worker_status": worker_status,
    }
    if worker_reason:
        response["worker_reason"] = worker_reason
    return response


def _worker_state_file_path() -> Path:
    backend_dir = Path(__file__).resolve().parents[4]
    configured = os.getenv("WORKER_HEALTH_STATE_FILE", ".worker-health.json").strip()
    filename = Path(configured).name or ".worker-health.json"
    return backend_dir / filename


def _read_worker_state_file(state_file: Path) -> dict[str, Any]:
    try:
        content = state_file.read_text(encoding="utf-8")
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return {}
    return {}
