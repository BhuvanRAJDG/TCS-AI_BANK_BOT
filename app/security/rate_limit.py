"""
app/security/rate_limit.py
Sliding-window rate limiter backed by an in-process dict.
Swappable with Redis for production.
"""
import time
import threading
from functools import wraps
from flask import request, jsonify

from .device import get_client_ip

_LOCK   = threading.Lock()
_STORE: dict[str, list[float]] = {}   # key -> list of UNIX timestamps


def _sliding_window_check(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """
    Returns (allowed, remaining_seconds_until_reset).
    Mutates _STORE.
    """
    now = time.time()
    cutoff = now - window_seconds
    with _LOCK:
        hits = _STORE.get(key, [])
        hits = [t for t in hits if t > cutoff]   # drop expired entries
        if len(hits) >= max_requests:
            retry_after = int(hits[0] + window_seconds - now) + 1
            _STORE[key] = hits
            return False, retry_after
        hits.append(now)
        _STORE[key] = hits
    return True, 0


def _make_key(prefix: str, identifier: str) -> str:
    return f"rl:{prefix}:{identifier}"


# ── decorator factory ─────────────────────────────────────────────────────────

def rate_limit(max_requests: int = 5, window_seconds: int = 60,
               key_func=None, scope: str = 'global'):
    """
    Decorator: return 429 if the caller exceeds max_requests in window_seconds.

    key_func(request) -> str   — defaults to client IP
    scope                       — logical label used in the cache key
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            identifier = key_func(request) if key_func else get_client_ip()
            key = _make_key(scope, identifier)
            allowed, retry_after = _sliding_window_check(key, max_requests, window_seconds)
            if not allowed:
                resp = jsonify({
                    'error': 'Too many requests. Please try again later.',
                    'retry_after_seconds': retry_after,
                })
                resp.status_code = 429
                resp.headers['Retry-After'] = str(retry_after)
                return resp
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── named presets ─────────────────────────────────────────────────────────────

def login_rate_limit(f):
    """5 login attempts per 10 minutes per IP."""
    return rate_limit(max_requests=5, window_seconds=600, scope='login')(f)


def otp_rate_limit(f):
    """3 OTP verifications per 5 minutes per IP."""
    return rate_limit(max_requests=3, window_seconds=300, scope='otp')(f)


def register_rate_limit(f):
    """10 registration attempts per hour per IP."""
    return rate_limit(max_requests=10, window_seconds=3600, scope='register')(f)
