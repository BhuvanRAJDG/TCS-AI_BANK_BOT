"""
app/routes/__init__.py
"""
from .dashboard import dashboard_bp
from .transactions import transactions_bp
from .loans import loans_bp
from .insurance import insurance_bp
from .notifications import notifications_bp
from .profile import profile_bp

__all__ = [
    'dashboard_bp',
    'transactions_bp',
    'loans_bp',
    'insurance_bp',
    'notifications_bp',
    'profile_bp'
]
