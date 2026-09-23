"""
app/auth/otp_service.py
Console-mock OTP service.

Storage: in-process dict — replace with Redis for production.
"""
import random
import time
import threading

_LOCK  = threading.Lock()
_STORE: dict[int, dict] = {}   # user_id -> {otp, expires_at, attempts}

OTP_TTL_SECONDS = 300   # 5 minutes
MAX_ATTEMPTS    = 3


def generate_otp(user_id: int) -> str:
    """
    Generate and store a 6-digit OTP for user_id.
    Returns '123456' in dev mode, or random 6-digit in production.
    """
    import os
    if os.getenv('FLASK_ENV') != 'production':
        otp = "123456"
    else:
        otp = f"{random.randint(0, 999999):06d}"

    with _LOCK:
        _STORE[user_id] = {
            'otp':        otp,
            'expires_at': time.time() + OTP_TTL_SECONDS,
            'attempts':   0,
        }
    return otp


def verify_otp(user_id: int, submitted: str) -> tuple[bool, str]:
    """
    Validate the submitted OTP.
    Returns (success, reason_message).
    """
    with _LOCK:
        record = _STORE.get(user_id)
        if not record:
            return False, 'No OTP found. Please request a new one.'

        if time.time() > record['expires_at']:
            _STORE.pop(user_id, None)
            return False, 'OTP has expired. Please request a new one.'

        if record['attempts'] >= MAX_ATTEMPTS:
            _STORE.pop(user_id, None)
            return False, 'Too many incorrect attempts. Please request a new OTP.'

        record['attempts'] += 1

        if submitted != record['otp']:
            remaining = MAX_ATTEMPTS - record['attempts']
            return False, f'Incorrect OTP. {remaining} attempt(s) remaining.'

        # success – consume the OTP
        _STORE.pop(user_id, None)
        return True, 'OTP verified.'


def invalidate_otp(user_id: int):
    """Manually invalidate any pending OTP for this user."""
    with _LOCK:
        _STORE.pop(user_id, None)
