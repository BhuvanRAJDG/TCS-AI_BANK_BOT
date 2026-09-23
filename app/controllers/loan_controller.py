"""
app/controllers/loan_controller.py
"""
from flask import jsonify, g
from app.services.loan_service import LoanService
from app.models import CustomerProfile


class LoanController:
    @staticmethod
    def get_loans():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1
        return jsonify({'status': 'success', 'data': LoanService.get_user_loans(customer_id)}), 200

    @staticmethod
    def get_emis():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1
        return jsonify({'status': 'success', 'data': LoanService.get_user_emis(customer_id)}), 200

    @staticmethod
    def get_credit_score():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1
        return jsonify({'status': 'success', 'data': LoanService.get_credit_score_details(customer_id)}), 200
