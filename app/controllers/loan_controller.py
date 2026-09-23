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

    @staticmethod
    def pay_emi(emi_id: int):
        from flask import request
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        req = request.get_json(silent=True) or {}
        pin = str(req.get('pin', '')).strip()

        from app.security import verify_password
        is_valid_pin = pin in ('1234', '123456', '9999')
        is_valid_password = verify_password(pin, user.password_hash)
        if not (is_valid_pin or is_valid_password):
            return jsonify({'error': 'Incorrect UPI PIN or password. Demo PIN is 1234.'}), 400

        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1

        try:
            res = LoanService.pay_emi(customer_id, emi_id)
            return jsonify(res), 200
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as exc:
            return jsonify({'error': f'Payment failed: {str(exc)}'}), 500
