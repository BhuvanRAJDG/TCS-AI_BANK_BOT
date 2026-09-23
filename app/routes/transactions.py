"""
app/routes/transactions.py
"""
from flask import Blueprint, render_template, jsonify
from app.controllers.transaction_controller import TransactionController

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/transactions')
def page():
    return render_template('pages/transactions.html')

@transactions_bp.route('/transactions/<int:tx_id>')
def detail_page(tx_id):
    return render_template('pages/transaction_detail.html', tx_id=tx_id)

@transactions_bp.route('/api/transactions', methods=['GET'])
def api_list():
    return TransactionController.get_transactions()

@transactions_bp.route('/api/transactions/<int:tx_id>', methods=['GET'])
def api_detail(tx_id):
    return TransactionController.get_transaction_detail(tx_id)

@transactions_bp.route('/api/transactions/transfer', methods=['POST'])
def api_transfer():
    return TransactionController.transfer_money()