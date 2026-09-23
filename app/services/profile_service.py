"""
app/services/profile_service.py
"""
from app import db
from app.models import User, CustomerProfile, Account


class ProfileService:
    @staticmethod
    def get_profile(user_id):
        user     = User.query.get(user_id)
        if not user:
            return None
        customer = CustomerProfile.query.filter_by(user_id=user_id).first()
        accounts = Account.query.filter_by(customer_id=customer.id).all() if customer else []

        return {
            'user_id':            user.id,
            'email':              user.email,
            'role':               user.role.value if hasattr(user.role, 'value') else str(user.role),
            'mfa_enabled':        getattr(user, 'mfa_enabled', False),
            'preferred_language': getattr(user, 'preferred_language', 'en'),
            'customer': {
                'id':              customer.id,
                'full_name':       customer.name,
                'phone':           customer.phone or 'N/A',
                'pan_masked':      customer.pan_masked or 'XXXXX1234X',
                'aadhaar_masked':  customer.aadhaar_masked or 'XXXX-XXXX-1234',
                'city':            customer.city or 'Bangalore',
                'state':           customer.state or 'Karnataka',
                'kyc_status':      customer.kyc_status
            } if customer else None,
            'accounts': [{
                'account_number': acc.account_number,
                'account_type':   acc.account_type,
                'balance':        float(acc.balance or 0),
                'ifsc':           acc.ifsc_code,
                'is_active':      acc.is_active
            } for acc in accounts]
        }

    @staticmethod
    def update_settings(user_id, language=None, mfa_enabled=None):
        user = User.query.get(user_id)
        if not user:
            return False
        if language and hasattr(user, 'preferred_language'):
            user.preferred_language = language
        if mfa_enabled is not None and hasattr(user, 'mfa_enabled'):
            user.mfa_enabled = mfa_enabled
        db.session.commit()
        return True
