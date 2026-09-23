"""
app/controllers/dashboard_controller.py
"""
from flask import jsonify, g
from app import db
from app.services.dashboard_service import DashboardService
from app.models import CustomerProfile, Account, User


class DashboardController:
    @staticmethod
    def get_dashboard_data():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        customer = CustomerProfile.query.filter_by(user_id=user.id).first()
        if not customer:
            customer = CustomerProfile(
                user_id=user.id,
                name=user.email.split('@')[0].capitalize(),
                kyc_status='verified'
            )
            db.session.add(customer)
            db.session.commit()

        # Ensure user has at least one active bank account
        acc = Account.query.filter_by(customer_id=customer.id).first()
        if not acc:
            import random
            acc = Account(
                customer_id=customer.id,
                account_number=f"1000{random.randint(100000, 999999)}",
                account_type="savings",
                balance=50000.00,
                currency="INR",
                ifsc_code="SENT0001001",
                is_active=True
            )
            db.session.add(acc)
            db.session.commit()

        summary = DashboardService.get_dashboard_summary(customer.id)
        return jsonify({'status': 'success', 'data': summary}), 200