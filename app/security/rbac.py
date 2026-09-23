"""
app/security/rbac.py
Role-Based Access Control decorators.
"""
from functools import wraps
from flask import jsonify, g

from .jwt import jwt_required


# ── role hierarchy ─────────────────────────────────────────────────────────────

ROLE_HIERARCHY = {
    'customer':   0,
    'bank_agent': 1,
    'admin':      2,
}


def roles_required(*allowed_roles: str):
    """
    Decorator that:
      1. Validates the JWT (via jwt_required).
      2. Checks that the authenticated user's role is in allowed_roles.

    Usage:
        @roles_required('admin')
        @roles_required('bank_agent', 'admin')
    """
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({'error': 'Not authenticated'}), 401
            if user.role not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden',
                    'required_roles': list(allowed_roles),
                    'your_role': user.role,
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def min_role(min_role_name: str):
    """
    Decorator: allows the role and anything above it in the hierarchy.
    """
    min_level = ROLE_HIERARCHY.get(min_role_name, 0)

    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({'error': 'Not authenticated'}), 401
            user_level = ROLE_HIERARCHY.get(user.role, -1)
            if user_level < min_level:
                return jsonify({'error': 'Insufficient privileges'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def current_user_is(role: str) -> bool:
    """Helper used inside route functions after jwt_required."""
    user = getattr(g, 'current_user', None)
    return user is not None and user.role == role


def current_user_owns_account(account_customer_id: int) -> bool:
    """Return True if the current user is the owner of the given customer record."""
    user = getattr(g, 'current_user', None)
    if not user:
        return False
    if user.role in ('admin', 'bank_agent'):
        return True
    profile = getattr(user, 'customer_profile', None)
    return profile is not None and profile.id == account_customer_id
