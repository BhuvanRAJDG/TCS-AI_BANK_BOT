"""
app/controllers/transaction_controller.py
"""
from flask import request, jsonify, g
from app import db
from app.services.transaction_service import TransactionService
from app.models import CustomerProfile


class TransactionController:
    @staticmethod
    def get_transactions():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        customer = CustomerProfile.query.filter_by(user_id=user.id).first()
        if not customer:
            return jsonify({'status': 'success', 'data': {'items': [], 'total': 0, 'pages': 0, 'current_page': 1}}), 200

        data = TransactionService.get_user_transactions(
            customer.id,
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
        customer = CustomerProfile.query.filter_by(user_id=user.id).first()
        if not customer:
            return jsonify({'error': 'Customer record not found'}), 404

        data = TransactionService.get_transaction_detail(customer.id, tx_id)
        if not data:
            return jsonify({'error': 'Transaction not found'}), 404
        return jsonify({'status': 'success', 'data': data}), 200

    @staticmethod
    def transfer_money():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        customer = CustomerProfile.query.filter_by(user_id=user.id).first()
        if not customer:
            return jsonify({'error': 'Customer record not found'}), 400

        body = request.get_json(silent=True) or request.form.to_dict() or {}
        recipient = (body.get('recipient') or '').strip()
        remark = (body.get('remark') or 'Direct Transfer').strip()
        try:
            amount = float(body.get('amount', 0))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount entered.'}), 400

        if not recipient:
            return jsonify({'error': 'Recipient name or account is required.'}), 400
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than zero.'}), 400

        try:
            receipt = TransactionService.process_transfer(
                sender_customer_id=customer.id,
                recipient_name_or_target=recipient,
                amount=amount,
                remark=remark
            )
            return jsonify({
                'status': 'success',
                'message': f'Transferred ₹{amount:,.2f} to {recipient} successfully!',
                'receipt': receipt
            }), 200
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as exc:
            return jsonify({'error': f'Transfer failed: {str(exc)}'}), 500