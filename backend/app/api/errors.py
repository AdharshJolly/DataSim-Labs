"""Global API error and request-id handling."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"


def _get_request_id(request: Request) -> str:
    existing = request.headers.get(REQUEST_ID_HEADER)
    if existing:
        return existing
    return str(uuid.uuid4())


def _build_error_payload(
    *,
    request_id: str,
    code: str,
    message: str,
    details: object | None = None,
) -> dict[str, object]:
    error_body: dict[str, object] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        error_body["details"] = details

    payload: dict[str, object] = {
        "success": False,
        "error": error_body,
    }
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request_id = _get_request_id(request)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", _get_request_id(request))
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Request failed"
        payload = _build_error_payload(
            request_id=request_id,
            code=f"http_{exc.status_code}",
            message=message,
            details=detail if not isinstance(detail, str) else None,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers={REQUEST_ID_HEADER: request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        request_id = getattr(request.state, "request_id", _get_request_id(request))
        payload = _build_error_payload(
            request_id=request_id,
            code="validation_error",
            message="Input validation failed",
            details=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=payload,
            headers={REQUEST_ID_HEADER: request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", _get_request_id(request))
        logger.exception("Unhandled API exception request_id=%s", request_id)
        payload = _build_error_payload(
            request_id=request_id,
            code="internal_error",
            message="Internal server error",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload,
            headers={REQUEST_ID_HEADER: request_id},
        )
