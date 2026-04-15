"""Shared auth helpers for privileged API routes.

God-mode and media endpoints are powerful side-effecting operations. They must
be gated behind an explicit opt-in env flag and (optionally) an admin token.

Environment variables:
    GOD_MODE_ENABLED     "1" to enable the god-mode router at all. Default off.
    ADMIN_TOKEN          If set, god-mode + media mutation endpoints require
                         header `X-Admin-Token: <value>`.
    MEDIA_AUTH_REQUIRED  "1" to require ADMIN_TOKEN on media generation routes.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request


def god_mode_enabled() -> bool:
    return os.getenv("GOD_MODE_ENABLED", "0") == "1"


def media_auth_required() -> bool:
    return os.getenv("MEDIA_AUTH_REQUIRED", "0") == "1"


def _check_token(provided: str | None) -> None:
    expected = os.getenv("ADMIN_TOKEN")
    if expected and provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Dependency: reject if ADMIN_TOKEN is set and the header does not match."""
    _check_token(x_admin_token)


def require_admin_if_media(x_admin_token: str | None = Header(default=None)) -> None:
    """Dependency: only enforce admin token when MEDIA_AUTH_REQUIRED=1."""
    if media_auth_required():
        _check_token(x_admin_token)


# ── Simple in-process rate limiter (per-IP token bucket approximation) ──
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request, key: str, max_calls: int, window_seconds: float) -> None:
    """Reject if `key`+client IP exceeds `max_calls` within `window_seconds`.

    In-process only — fine for a single-backend dev/prod, not for horizontal scale.
    """
    ip = request.client.host if request.client else "unknown"
    bucket = _hits[f"{key}:{ip}"]
    now = time.monotonic()
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_calls:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)
