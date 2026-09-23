"""
app/auth/routes.py
Full authentication REST API.

Endpoints
─────────
POST /auth/register       — create account
POST /auth/login          — email + password → tokens
POST /auth/mfa/request    — request OTP (requires pending_mfa cookie)
POST /auth/mfa/verify     — verify OTP → full tokens
POST /auth/refresh        — exchange refresh token → new access token
POST /auth/logout         — revoke current refresh token
POST /auth/logout-all     — revoke ALL sessions
GET  /auth/me             — current user info (jwt_required)
"""
import re
from datetime import datetime

from flask import Blueprint, request, jsonify, make_response, g, current_app

from .. import db
from ..models.user          import User
from ..models.customer      import CustomerProfile
from ..models.notification  import Notification

from ..security import (
    hash_password, verify_password, assert_password_strong, PasswordStrengthError,
    create_access_token, create_refresh_token,
    persist_refresh_session, revoke_session_by_token, revoke_all_sessions,
    decode_token, jwt_required,
    login_rate_limit, otp_rate_limit, register_rate_limit,
    get_client_ip, build_device_info,
    log_login_success, log_login_failure, log_logout, log_mfa_event,
)
from .otp_service import generate_otp, verify_otp

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ── helpers ───────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

MAX_FAILED_LOGINS = 5       # lock after this many consecutive failures
FAILED_LOCK_DURATION = 900  # 15 minutes (stored in session-level cache for now)

# Simple in-memory failed-login tracker {email: [timestamps]}
_failed_logins: dict[str, list[datetime]] = {}


def _record_failure(email: str):
    now = datetime.utcnow()
    _failed_logins.setdefault(email, [])
    _failed_logins[email].append(now)


def _is_locked(email: str) -> bool:
    import time
    window = FAILED_LOCK_DURATION
    now = datetime.utcnow().timestamp()
    hits = [t for t in _failed_logins.get(email, [])
            if (now - t.timestamp()) < window]
    _failed_logins[email] = hits
    return len(hits) >= MAX_FAILED_LOGINS


def _clear_failures(email: str):
    _failed_logins.pop(email, None)


def _sanitize(value: str) -> str:
    """Basic XSS protection: strip angle-bracket tags."""
    return re.sub(r'<[^>]*>', '', value).strip()


def _set_token_cookies(response, access_token: str, refresh_token: str):
    secure = not current_app.config.get('FLASK_DEBUG', True)
    response.set_cookie('access_token', access_token,
                        httponly=True, samesite='Strict', secure=secure,
                        max_age=60 * int(current_app.config.get('JWT_ACCESS_MINUTES', 15)))
    response.set_cookie('refresh_token', refresh_token,
                        httponly=True, samesite='Strict', secure=secure,
                        max_age=86400 * int(current_app.config.get('JWT_REFRESH_DAYS', 30)))


# ── POST /auth/register ───────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
@register_rate_limit
def register():
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    email    = _sanitize(data.get('email', ''))
    password = data.get('password', '')
    confirm  = data.get('confirm_password', '')
    name     = _sanitize(data.get('name') or data.get('full_name', ''))
    phone    = _sanitize(data.get('phone', ''))
    language = data.get('preferred_language', 'en')

    # ── validation ────────────────────────────────────────────────────────────
    errors = {}
    if not _EMAIL_RE.match(email):
        errors['email'] = 'Invalid email address.'
    if not name:
        errors['name'] = 'Name is required.'
    if password != confirm:
        errors['confirm_password'] = 'Passwords do not match.'
    try:
        assert_password_strong(password)
    except PasswordStrengthError as e:
        errors['password'] = str(e)
    if errors:
        return jsonify({'errors': errors}), 422

    if User.query.filter_by(email=email).first():
        return jsonify({'errors': {'email': 'Email already registered.'}}), 409

    # ── create user + customer profile ────────────────────────────────────────
    user = User(
        email         = email,
        password_hash = hash_password(password),
        phone         = phone or None,
        role          = 'customer',
        mfa_enabled   = False,
    )
    db.session.add(user)
    db.session.flush()

    profile = CustomerProfile(
        user_id            = user.id,
        name               = name,
        phone              = phone or None,
        preferred_language = language if language in ('en','kn','hi','ta','te','mr','bn','gu','pa') else 'en',
        kyc_status         = 'pending',
    )
    db.session.add(profile)

    # welcome notification
    notif = Notification(
        user_id    = user.id,
        title      = 'Welcome to CBS Bank',
        body       = f'Hi {name}, your account has been created. Complete KYC to unlock all features.',
        notif_type = 'system',
        channel    = 'in_app',
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        'message': 'Registration successful.',
        'user_id': user.id,
    }), 201


# ── POST /auth/login ──────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
@login_rate_limit
def login():
    data  = request.get_json(silent=True) or request.form.to_dict() or {}
    email = _sanitize(data.get('email', ''))
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    # account lock check
    if _is_locked(email):
        return jsonify({'error': 'Account temporarily locked. Try again in 15 minutes.'}), 423

    user = User.query.filter_by(email=email).first()

    if not user or not verify_password(password, user.password_hash):
        _record_failure(email)
        log_login_failure(email)
        db.session.commit()
        remaining = MAX_FAILED_LOGINS - len(_failed_logins.get(email, []))
        return jsonify({
            'error': 'Invalid email or password.',
            'attempts_remaining': max(0, remaining),
        }), 401

    if not user.is_active:
        return jsonify({'error': 'Account is deactivated. Contact support.'}), 403

    _clear_failures(email)

    # ── MFA required? ─────────────────────────────────────────────────────────
    if user.mfa_enabled:
        otp = generate_otp(user.id)
        print(f"[SENTINEL OTP] user_id={user.id} email={email} otp={otp}")  # console mock
        resp = make_response(jsonify({'mfa_required': True,
                                      'message': 'OTP sent. Check console/email.'}), 200)
        # Store a short-lived pending cookie so the MFA endpoint knows who is verifying
        resp.set_cookie('pending_mfa_uid', str(user.id),
                        httponly=True, samesite='Strict',
                        max_age=300)   # 5 minutes
        return resp

    # ── Issue tokens ──────────────────────────────────────────────────────────
    access_token            = create_access_token(user.id, user.role)
    refresh_token, exp      = create_refresh_token(user.id)
    persist_refresh_session(user.id, refresh_token, exp,
                             ip=get_client_ip(), device_info=build_device_info())

    log_login_success(user.id)
    db.session.commit()

    resp = make_response(jsonify({
        'access_token':  access_token,
        'token_type':    'Bearer',
        'expires_in':    int(current_app.config.get('JWT_ACCESS_MINUTES', 15)) * 60,
        'role':          user.role,
    }), 200)
    _set_token_cookies(resp, access_token, refresh_token)
    return resp


# ── POST /auth/mfa/request ────────────────────────────────────────────────────

@auth_bp.route('/mfa/request', methods=['POST'])
def mfa_request():
    uid_str = request.cookies.get('pending_mfa_uid')
    if not uid_str:
        return jsonify({'error': 'No pending MFA session.'}), 400
    user = User.query.get(int(uid_str))
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    otp = generate_otp(user.id)
    print(f"[SENTINEL OTP] Resend → user_id={user.id} otp={otp}")
    return jsonify({'message': 'OTP re-sent.'}), 200


# ── POST /auth/mfa/verify ─────────────────────────────────────────────────────

@auth_bp.route('/mfa/verify', methods=['POST'])
@otp_rate_limit
def mfa_verify():
    uid_str = request.cookies.get('pending_mfa_uid')
    if not uid_str:
        return jsonify({'error': 'No pending MFA session.'}), 400

    data = request.get_json(silent=True) or {}
    otp  = str(data.get('otp', '')).strip()

    user_id = int(uid_str)
    valid, reason = verify_otp(user_id, otp)
    log_mfa_event(user_id, valid)

    if not valid:
        db.session.commit()
        return jsonify({'error': reason}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    access_token       = create_access_token(user.id, user.role)
    refresh_token, exp = create_refresh_token(user.id)
    persist_refresh_session(user.id, refresh_token, exp,
                             ip=get_client_ip(), device_info=build_device_info())

    log_login_success(user.id)
    db.session.commit()

    resp = make_response(jsonify({
        'access_token': access_token,
        'token_type':   'Bearer',
        'expires_in':   int(current_app.config.get('JWT_ACCESS_MINUTES', 15)) * 60,
        'role':         user.role,
    }), 200)
    _set_token_cookies(resp, access_token, refresh_token)
    resp.delete_cookie('pending_mfa_uid')
    return resp


# ── POST /auth/refresh ────────────────────────────────────────────────────────

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    token = (request.get_json(silent=True) or {}).get('refresh_token') \
            or request.cookies.get('refresh_token')
    if not token:
        return jsonify({'error': 'Refresh token required.'}), 400

    try:
        payload = decode_token(token)
        if payload.get('type') != 'refresh':
            raise ValueError()
    except Exception:
        return jsonify({'error': 'Invalid or expired refresh token.'}), 401

    from ..models.session import Session
    sess = Session.query.filter_by(refresh_token=token, is_active=True).first()
    if not sess or sess.is_expired:
        return jsonify({'error': 'Session expired or revoked.'}), 401

    user = User.query.get(int(payload['sub']))
    if not user or not user.is_active:
        return jsonify({'error': 'User not found.'}), 401

    new_access = create_access_token(user.id, user.role)
    resp = make_response(jsonify({'access_token': new_access, 'token_type': 'Bearer'}), 200)
    secure = not current_app.config.get('FLASK_DEBUG', True)
    resp.set_cookie('access_token', new_access,
                    httponly=True, samesite='Strict', secure=secure,
                    max_age=60 * int(current_app.config.get('JWT_ACCESS_MINUTES', 15)))
    return resp


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    token = (request.get_json(silent=True) or {}).get('refresh_token') \
            or request.cookies.get('refresh_token')
    if token:
        try:
            revoke_session_by_token(token)
        except Exception:
            pass

    user = getattr(g, 'current_user', None)
    if user:
        try:
            log_logout(user.id)
            db.session.commit()
        except Exception:
            pass

    if request.method == 'GET' or 'text/html' in request.headers.get('Accept', ''):
        from flask import redirect
        resp = make_response(redirect('/login'))
    else:
        resp = make_response(jsonify({'message': 'Logged out successfully.'}), 200)

    resp.delete_cookie('access_token')
    resp.delete_cookie('refresh_token')
    return resp


# ── POST /auth/verify-pin ─────────────────────────────────────────────────────

@auth_bp.route('/verify-pin', methods=['POST'])
def verify_pin():
    """
    Verify transaction authorization with user's UPI PIN or password.
    Accepts: { "pin": str }
    """
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'valid': False, 'error': 'Unauthorized — please log in'}), 401

    data = request.get_json(silent=True) or {}
    pin = str(data.get('pin', '')).strip()

    if not pin:
        return jsonify({'valid': False, 'error': 'PIN or password required'}), 400

    # Accept common UPI PINs (1234, 123456, 9999) OR actual account password
    is_valid_pin = pin in ('1234', '123456', '9999')
    is_valid_password = verify_password(pin, user.password_hash)

    if is_valid_pin or is_valid_password:
        return jsonify({
            'valid': True,
            'message': 'PIN verified successfully.'
        }), 200

    return jsonify({
        'valid': False,
        'error': 'Incorrect UPI PIN or password. Default demo PIN is 1234 or your account password.'
    }), 400



# ── POST /auth/logout-all ─────────────────────────────────────────────────────

@auth_bp.route('/logout-all', methods=['POST'])
@jwt_required
def logout_all():
    revoke_all_sessions(g.current_user.id)
    log_logout(g.current_user.id)
    db.session.commit()

    resp = make_response(jsonify({'message': 'All sessions revoked.'}), 200)
    resp.delete_cookie('access_token')
    resp.delete_cookie('refresh_token')
    return resp


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@auth_bp.route('/me', methods=['GET'])
@jwt_required
def me():
    user    = g.current_user
    profile = user.customer_profile
    return jsonify({
        'id':    user.id,
        'email': user.email,
        'role':  user.role,
        'mfa_enabled': user.mfa_enabled,
        'profile': {
            'name':               profile.name               if profile else None,
            'preferred_language': profile.preferred_language if profile else 'en',
            'kyc_status':         profile.kyc_status         if profile else None,
        } if profile else None,
    }), 200

