"""
app/security/jwt.py
JWT access + refresh token utilities.
"""
import os
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app, g

from .. import db
from ..models.session import Session
from ..models.user import User

_ALGORITHM = 'HS256'

# ── token creation ────────────────────────────────────────────────────────────

def _secret() -> str:
    return current_app.config['JWT_SECRET_KEY']


def create_access_token(user_id: int, role: str, extra: dict | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=int(current_app.config.get('JWT_ACCESS_MINUTES', 15))
    )
    payload = {
        'sub':  str(user_id),
        'role': role,
        'jti':  uuid.uuid4().hex,
        'iat':  datetime.now(timezone.utc),
        'exp':  exp,
        'type': 'access',
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """Returns (token_string, expiry_datetime)."""
    exp = datetime.now(timezone.utc) + timedelta(
        days=int(current_app.config.get('JWT_REFRESH_DAYS', 30))
    )
    payload = {
        'sub':  str(user_id),
        'jti':  uuid.uuid4().hex,
        'iat':  datetime.now(timezone.utc),
        'exp':  exp,
        'type': 'refresh',
    }
    token = jwt.encode(payload, _secret(), algorithm=_ALGORITHM)
    return token, exp


def decode_token(token: str) -> dict:
    """Raises jwt.* exceptions on failure."""
    return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])


# ── session persistence ───────────────────────────────────────────────────────

def persist_refresh_session(user_id: int, refresh_token: str,
                             expires_at: datetime,
                             ip: str | None = None,
                             device_info: str | None = None) -> Session:
    sess = Session(
        user_id       = user_id,
        refresh_token = refresh_token,
        ip_address    = ip,
        device_info   = device_info,
        expires_at    = expires_at,
        is_active     = True,
    )
    db.session.add(sess)
    db.session.commit()
    return sess


def revoke_session_by_token(refresh_token: str) -> bool:
    sess = Session.query.filter_by(refresh_token=refresh_token, is_active=True).first()
    if not sess:
        return False
    sess.revoke()
    db.session.commit()
    return True


def revoke_all_sessions(user_id: int):
    sessions = Session.query.filter_by(user_id=user_id, is_active=True).all()
    for s in sessions:
        s.revoke()
    db.session.commit()


# ── FLASK decorator ───────────────────────────────────────────────────────────

def jwt_required(f):
    """Decorator: validates Bearer token from Authorization header or cookie."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        if not token:
            token = request.cookies.get('access_token')
        if not token:
            return jsonify({'error': 'Missing access token'}), 401
        try:
            payload = decode_token(token)
            if payload.get('type') != 'access':
                raise ValueError('Not an access token')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401

        user = User.query.get(int(payload['sub']))
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401

        g.current_user = user
        g.jwt_payload  = payload
        return f(*args, **kwargs)
    return decorated
