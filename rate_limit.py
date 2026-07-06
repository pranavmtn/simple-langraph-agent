"""Per-IP request throttling for chat graph runs.

Uses an in-memory sliding window (resets on app reboot; single-container only).
IP is read from X-Forwarded-For on Streamlit Cloud; local dev falls back to
session key or st.context.ip_address.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass

import streamlit as st

RATE_LIMIT_FREE_REQUESTS = int(os.getenv("RATE_LIMIT_FREE_REQUESTS", "3"))
RATE_LIMIT_COOLDOWN_1_SEC = int(os.getenv("RATE_LIMIT_COOLDOWN_1_SEC", "60"))
RATE_LIMIT_COOLDOWN_2_SEC = int(os.getenv("RATE_LIMIT_COOLDOWN_2_SEC", "300"))
RATE_LIMIT_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "3600"))

_store: dict[str, list[float]] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    wait_seconds: int
    message: str


def get_client_ip() -> str:
    """Resolve client IP from proxy headers or local fallbacks."""
    try:
        headers = st.context.headers
        forwarded = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    except Exception:
        pass

    try:
        ip = st.context.ip_address
        if ip:
            return str(ip)
    except Exception:
        pass

    if "rate_limit_client_key" not in st.session_state:
        st.session_state.rate_limit_client_key = f"local-{uuid.uuid4()}"
    return st.session_state.rate_limit_client_key


def _trim(timestamps: list[float], now: float) -> list[float]:
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    return [t for t in timestamps if t >= cutoff]


def check_rate_limit(ip: str | None = None) -> RateLimitResult:
    """Return whether the next chat request is allowed and any wait time."""
    ip = ip or get_client_ip()
    now = time.time()

    with _lock:
        timestamps = _trim(_store.get(ip, []), now)
        _store[ip] = timestamps
        count = len(timestamps)

        if count < RATE_LIMIT_FREE_REQUESTS:
            return RateLimitResult(True, 0, "")

        last = timestamps[-1]
        cooldown = (
            RATE_LIMIT_COOLDOWN_1_SEC
            if count == RATE_LIMIT_FREE_REQUESTS
            else RATE_LIMIT_COOLDOWN_2_SEC
        )
        elapsed = now - last
        if elapsed < cooldown:
            remaining = max(1, int(cooldown - elapsed + 0.999))
            message = f"Please wait {remaining}s before sending another message."
            return RateLimitResult(False, remaining, message)

        return RateLimitResult(True, 0, "")


def record_request(ip: str | None = None) -> None:
    """Record a successful allowed chat request for rate limiting."""
    ip = ip or get_client_ip()
    now = time.time()

    with _lock:
        timestamps = _trim(_store.get(ip, []), now)
        timestamps.append(now)
        _store[ip] = timestamps
