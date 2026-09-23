"""
app/services/profile_service.py
"""
import random
import re
from datetime import datetime
from app import db
from app.models import User, CustomerProfile, Account, Transaction
from app.security.password import hash_password, verify_password, assert_password_strong, PasswordStrengthError


class ProfileService:
    @staticmethod
    def get_profile(user_id):
        user = User.query.get(user_id)
        if not user:
            return None

        customer = CustomerProfile.query.filter_by(user_id=user_id).first()
        if not customer:
            name_derived = user.email.split('@')[0].replace('.', ' ').title()
            customer = CustomerProfile(
                user_id=user.id,
                name=name_derived,
                phone=user.phone or "+91 98765 43210",
                pan_masked="ABCDE1234F",
                aadhaar_masked="XXXX-XXXX-9012",
                city="Mumbai",
                state="Maharashtra",
                kyc_status="verified"
            )
            db.session.add(customer)
            db.session.commit()

        # Ensure user has linked accounts
        accounts = Account.query.filter_by(customer_id=customer.id).all()
        if not accounts:
            acc = Account(
                customer_id=customer.id,
                account_number=f"1000{random.randint(100000, 999999)}",
                account_type="savings",
                balance=75000.00,
                currency="INR",
                ifsc_code="SENT0001001",
                is_active=True
            )
            db.session.add(acc)
            db.session.commit()

            # Add welcome initial deposit transaction
            init_tx = Transaction(
                account_id=acc.id,
                amount=75000.00,
                transaction_type='credit',
                description="Welcome Initial Deposit - CBS Bank Account Opening",
                category='deposit',
                reference_id="WEL" + hex(random.randint(10000000, 99999999))[2:].upper(),
                merchant="CBS Bank System",
                channel='netbanking',
                timestamp=datetime.utcnow(),
                balance_after=75000.00
            )
            db.session.add(init_tx)
            db.session.commit()

            accounts = [acc]

        has_upi_pin = bool(user.upi_pin_hash)

        return {
            'user_id':            user.id,
            'email':              user.email,
            'role':               user.role.value if hasattr(user.role, 'value') else str(user.role),
            'mfa_enabled':        getattr(user, 'mfa_enabled', False),
            'has_upi_pin':        has_upi_pin,
            'preferred_language': getattr(user, 'preferred_language', 'en'),
            'customer': {
                'id':              customer.id,
                'full_name':       customer.name or user.email.split('@')[0].capitalize(),
                'phone':           customer.phone or user.phone or '+91 98765 43210',
                'pan_masked':      customer.pan_masked or 'ABCDE1234F',
                'aadhaar_masked':  customer.aadhaar_masked or 'XXXX-XXXX-9012',
                'city':            customer.city or 'Mumbai',
                'state':           customer.state or 'Maharashtra',
                'kyc_status':      customer.kyc_status or 'verified'
            },
            'accounts': [{
                'account_number': acc.account_number,
                'account_type':   (acc.account_type or 'savings').capitalize(),
                'balance':        float(acc.balance or 0),
                'ifsc':           acc.ifsc_code or 'SENT0001001',
                'is_active':      acc.is_active
            } for acc in accounts]
        }

    @staticmethod
    def set_or_reset_upi_pin(user_id: int, password: str, new_pin: str) -> dict:
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found.")

        if not password or not verify_password(password, user.password_hash):
            raise ValueError("Incorrect account password. Verification failed.")

        pin_clean = str(new_pin).strip()
        if not re.match(r"^\d{4,6}$", pin_clean):
            raise ValueError("UPI PIN must be exactly 4 to 6 numeric digits (0-9).")

        user.upi_pin_hash = hash_password(pin_clean)
        db.session.commit()
        return {"status": "success", "message": "UPI PIN set and updated successfully!"}

    @staticmethod
    def verify_user_upi_pin(user_id: int, entered_pin: str) -> bool:
        user = User.query.get(user_id)
        if not user:
            return False

        entered_pin = str(entered_pin).strip()
        if not entered_pin:
            return False

        # 1. Custom UPI PIN
        if user.upi_pin_hash:
            if verify_password(entered_pin, user.upi_pin_hash):
                return True

        # 2. Account Password fallback
        if verify_password(entered_pin, user.password_hash):
            return True

        # 3. Default demo PIN if not configured
        if not user.upi_pin_hash and entered_pin in ('1234', '123456'):
            return True

        return False

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> dict:
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found.")

        if not current_password or not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")

        try:
            assert_password_strong(new_password)
        except PasswordStrengthError as pe:
            raise ValueError(str(pe))

        user.password_hash = hash_password(new_password)
        db.session.commit()
        return {"status": "success", "message": "Account password changed successfully."}

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