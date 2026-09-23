"""
app/controllers/insurance_controller.py
"""
from flask import jsonify, g
from app.services.insurance_service import InsuranceService
from app.models import CustomerProfile


class InsuranceController:
    @staticmethod
    def get_policies():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1
        return jsonify({'status': 'success', 'data': InsuranceService.get_user_policies(customer_id)}), 200
