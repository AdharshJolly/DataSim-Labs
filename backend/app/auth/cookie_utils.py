"""Authentication cookie and request-key helper utilities."""

from __future__ import annotations

from fastapi import Request, Response

from app.core.config import settings


def _client_key(request: Request, route_name: str, identity: str = "") -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
    ident = identity.strip().lower() if identity else "anonymous"
    return f"{route_name}:{client_ip}:{ident}"


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    secure_cookie = settings.auth_cookie_secure or settings.app_env == "production"
    common_kwargs = {
        "httponly": True,
        "secure": secure_cookie,
        "samesite": settings.auth_cookie_samesite,
        "path": settings.auth_cookie_path,
    }
    if settings.auth_cookie_domain:
        common_kwargs["domain"] = settings.auth_cookie_domain

    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=access_token,
        max_age=settings.jwt_expiration_minutes * 60,
        **common_kwargs,
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        max_age=settings.jwt_refresh_expiration_days * 24 * 60 * 60,
        **common_kwargs,
    )


def _clear_auth_cookies(response: Response) -> None:
    secure_cookie = settings.auth_cookie_secure or settings.app_env == "production"
    clear_kwargs = {
        "secure": secure_cookie,
        "samesite": settings.auth_cookie_samesite,
        "path": settings.auth_cookie_path,
    }
    if settings.auth_cookie_domain:
        clear_kwargs["domain"] = settings.auth_cookie_domain

    response.delete_cookie(key=settings.auth_access_cookie_name, **clear_kwargs)
    response.delete_cookie(key=settings.auth_refresh_cookie_name, **clear_kwargs)
