"""app/security/__init__.py — public API for the security package."""

from .jwt        import (create_access_token, create_refresh_token, decode_token,
                          persist_refresh_session, revoke_session_by_token,
                          revoke_all_sessions, jwt_required)
from .password   import hash_password, verify_password, assert_password_strong, PasswordStrengthError
from .rbac       import roles_required, min_role, current_user_owns_account
from .device     import get_device_fingerprint, get_client_ip, build_device_info
from .rate_limit import rate_limit, login_rate_limit, otp_rate_limit, register_rate_limit
from .audit      import (log_event, log_login_success, log_login_failure,
                          log_logout, log_password_change, log_mfa_event)

__all__ = [
    # jwt
    'create_access_token', 'create_refresh_token', 'decode_token',
    'persist_refresh_session', 'revoke_session_by_token', 'revoke_all_sessions',
    'jwt_required',
    # password
    'hash_password', 'verify_password', 'assert_password_strong', 'PasswordStrengthError',
    # rbac
    'roles_required', 'min_role', 'current_user_owns_account',
    # device
    'get_device_fingerprint', 'get_client_ip', 'build_device_info',
    # rate_limit
    'rate_limit', 'login_rate_limit', 'otp_rate_limit', 'register_rate_limit',
    # audit
    'log_event', 'log_login_success', 'log_login_failure',
    'log_logout', 'log_password_change', 'log_mfa_event',
]
