"""
app/routes/loans.py
"""
from flask import Blueprint, render_template
from app.controllers.loan_controller import LoanController

loans_bp = Blueprint('loans', __name__)

@loans_bp.route('/loans')
def loans_page():
    return render_template('pages/loans.html')

@loans_bp.route('/emi')
def emi_page():
    return render_template('pages/emi.html')

@loans_bp.route('/credit-score')
def credit_score_page():
    return render_template('pages/credit_score.html')

@loans_bp.route('/api/loans', methods=['GET'])
def api_loans():
    return LoanController.get_loans()

@loans_bp.route('/api/emis', methods=['GET'])
def api_emis():
    return LoanController.get_emis()

@loans_bp.route('/api/emis/<int:emi_id>/pay', methods=['POST'])
def api_pay_emi(emi_id):
    return LoanController.pay_emi(emi_id)

@loans_bp.route('/api/credit-score', methods=['GET'])
def api_credit_score():
    return LoanController.get_credit_score()

