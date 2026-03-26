"""Simple auth rate limiting for login/register/refresh endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class LimitPolicy:
    max_requests: int
    window_seconds: int


class AuthRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, policy: LimitPolicy) -> None:
        now = time.time()
        bucket = self._buckets[key]
        cutoff = now - policy.window_seconds

        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= policy.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again later.",
            )

        bucket.append(now)


rate_limiter = AuthRateLimiter()

LOGIN_POLICY = LimitPolicy(max_requests=8, window_seconds=60)
REGISTER_POLICY = LimitPolicy(max_requests=6, window_seconds=60)
REFRESH_POLICY = LimitPolicy(max_requests=20, window_seconds=60)
