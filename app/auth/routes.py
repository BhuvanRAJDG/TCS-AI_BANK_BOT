"""
app/auth/routes.py
Full authentication REST API with user provisioning & individual accounts.
"""
import re
import random
from datetime import datetime

from flask import Blueprint, request, jsonify, make_response, g, current_app

from .. import db
from ..models.user          import User
from ..models.customer      import CustomerProfile
from ..models.account       import Account
from ..models.transaction   import Transaction
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

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MAX_FAILED_LOGINS = 5
FAILED_LOCK_DURATION = 900
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
    return re.sub(r'<[^>]*>', '', value).strip()


def _set_token_cookies(response, access_token: str, refresh_token: str):
    secure = not current_app.config.get('FLASK_DEBUG', True)
    response.set_cookie('access_token', access_token,
                        httponly=True, samesite='Strict', secure=secure,
                        max_age=60 * int(current_app.config.get('JWT_ACCESS_MINUTES', 15)))
    response.set_cookie('refresh_token', refresh_token,
                        httponly=True, samesite='Strict', secure=secure,
                        max_age=86400 * int(current_app.config.get('JWT_REFRESH_DAYS', 30)))


@auth_bp.route('/register', methods=['POST'])
@register_rate_limit
def register():
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    email    = _sanitize(data.get('email', ''))
    password = data.get('password', '')
    confirm  = data.get('confirm_password', '')
    name     = _sanitize(data.get('name') or data.get('full_name', ''))
    phone    = _sanitize(data.get('phone', ''))
    upi_pin  = _sanitize(data.get('upi_pin', '1234'))
    language = data.get('preferred_language', 'en')

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

    pin_hash = hash_password(upi_pin) if upi_pin else hash_password('1234')
    user = User(
        email         = email,
        password_hash = hash_password(password),
        upi_pin_hash  = pin_hash,
        phone         = phone or None,
        role          = 'customer',
        mfa_enabled   = False,
    )
    db.session.add(user)
    db.session.flush()

    random_pan = f"ABCDE{random.randint(1000, 9999)}F"
    random_aadhaar = f"XXXX-XXXX-{random.randint(1000, 9999)}"
    profile = CustomerProfile(
        user_id            = user.id,
        name               = name,
        phone              = phone or None,
        preferred_language = language if language in ('en','kn','hi','ta','te','mr','bn','gu','pa') else 'en',
        kyc_status         = 'verified',
        pan_masked         = random_pan,
        aadhaar_masked     = random_aadhaar,
        city               = "Mumbai",
        state              = "Maharashtra"
    )
    db.session.add(profile)
    db.session.flush()

    acc_num = f"1000{random.randint(100000, 999999)}"
    acc = Account(
        customer_id    = profile.id,
        account_number = acc_num,
        account_type   = "savings",
        balance        = 75000.00,
        currency       = "INR",
        ifsc_code      = "SENT0001001",
        is_active      = True
    )
    db.session.add(acc)
    db.session.flush()

    init_tx = Transaction(
        account_id       = acc.id,
        amount           = 75000.00,
        transaction_type = 'credit',
        description      = "Opening Balance Credit - CBS Bank Welcome Bonus",
        category         = 'deposit',
        reference_id     = "WEL" + hex(random.randint(10000000, 99999999))[2:].upper(),
        merchant         = "CBS Central Bank",
        channel          = 'netbanking',
        timestamp        = datetime.utcnow(),
        balance_after    = 75000.00
    )
    db.session.add(init_tx)

    notif = Notification(
        user_id    = user.id,
        title      = 'Welcome to CBS Bank AI',
        body       = f'Hi {name}, your CBS Savings Account ({acc_num}) is active with ₹75,000.00 balance.',
        notif_type = 'system',
        channel    = 'in_app',
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        'message': 'Registration successful. You can now log in.',
        'user_id': user.id,
        'account_number': acc_num
    }), 201


@auth_bp.route('/login', methods=['POST'])
@login_rate_limit
def login():
    data  = request.get_json(silent=True) or request.form.to_dict() or {}
    email = _sanitize(data.get('email', ''))
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

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

    _clear_failures(email)

    role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
    access_token = create_access_token(user.id, role_str)
    refresh_token, exp = create_refresh_token(user.id)

    dev_info = build_device_info()
    persist_refresh_session(user.id, refresh_token, exp, get_client_ip(), dev_info)
    log_login_success(user.id)
    db.session.commit()

    resp = make_response(jsonify({
        'message':       'Login successful.',
        'access_token':  access_token,
        'refresh_token': refresh_token,
        'user': {
            'id':    user.id,
            'email': user.email,
            'role':  role_str,
        },
    }), 200)

    _set_token_cookies(resp, access_token, refresh_token)
    return resp


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    from flask import redirect
    user = getattr(g, 'current_user', None)
    if user:
        revoke_all_sessions(user.id)
        db.session.commit()

    resp = make_response(redirect('/login'))
    resp.delete_cookie('access_token')
    resp.delete_cookie('refresh_token')
    return resp