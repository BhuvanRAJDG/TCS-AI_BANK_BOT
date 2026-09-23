"""
app/security/audit.py
Convenience wrapper for writing AuditLog rows.
"""
import json
from flask import request, g

from .. import db
from ..models.audit_log import AuditLog
from .device import get_client_ip


def log_event(
    action: str,
    *,
    entity_type: str | None = None,
    entity_id:   int | None = None,
    details:     dict | None = None,
    severity:    str = 'info',
    user_id:     int | None = None,
):
    """
    Write one AuditLog row.  Automatically picks up the authenticated user
    from Flask's g.current_user when user_id is not supplied explicitly.
    """
    uid = user_id
    if uid is None:
        current = getattr(g, 'current_user', None)
        if current:
            uid = current.id

    entry = AuditLog(
        user_id     = uid,
        action      = action[:100],
        entity_type = entity_type,
        entity_id   = entity_id,
        ip_address  = get_client_ip(),
        user_agent  = request.headers.get('User-Agent', '')[:500],
        details     = json.dumps(details) if details else None,
        severity    = severity,
    )
    db.session.add(entry)
    # Flush only – caller is responsible for db.session.commit()
    db.session.flush()


def log_login_success(user_id: int):
    log_event('LOGIN', entity_type='User', entity_id=user_id,
              details={'status': 'success'}, severity='info', user_id=user_id)


def log_login_failure(email: str):
    log_event('LOGIN_FAILED', entity_type='User',
              details={'email': email, 'status': 'failure'}, severity='warning')


def log_logout(user_id: int):
    log_event('LOGOUT', entity_type='User', entity_id=user_id,
              severity='info', user_id=user_id)


def log_password_change(user_id: int):
    log_event('CHANGE_PASSWORD', entity_type='User', entity_id=user_id,
              severity='warning', user_id=user_id)


def log_mfa_event(user_id: int, success: bool):
    log_event(
        'MFA_VERIFY',
        entity_type='User', entity_id=user_id,
        details={'success': success},
        severity='info' if success else 'warning',
        user_id=user_id,
    )
