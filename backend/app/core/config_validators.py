"""Reusable configuration validation helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def _is_upstash_host(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.hostname and parsed.hostname.endswith("upstash.io"))


def _validate_upstash_tls(url: str, field_name: str) -> None:
    if not url:
        return
    parsed = urlparse(url)
    if _is_upstash_host(url) and parsed.scheme != "rediss":
        raise ValueError(f"{field_name} uses Upstash and must use rediss:// (TLS).")
