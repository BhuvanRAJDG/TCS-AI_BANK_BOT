"""
app/controllers/transaction_controller.py
"""
from flask import request, jsonify, g
from app.services.transaction_service import TransactionService
from app.models import CustomerProfile


class TransactionController:
    @staticmethod
    def get_transactions():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1

        data = TransactionService.get_user_transactions(
            customer_id,
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 15, type=int),
            category=request.args.get('category'),
            tx_type=request.args.get('tx_type'),
            search=request.args.get('search')
        )
        return jsonify({'status': 'success', 'data': data}), 200

    @staticmethod
    def get_transaction_detail(tx_id):
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1

        data = TransactionService.get_transaction_detail(customer_id, tx_id)
        if not data:
            return jsonify({'error': 'Transaction not found'}), 404
        return jsonify({'status': 'success', 'data': data}), 200
