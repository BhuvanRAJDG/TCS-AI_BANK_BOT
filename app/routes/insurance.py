"""
app/routes/insurance.py
"""
from flask import Blueprint, render_template
from app.controllers.insurance_controller import InsuranceController

insurance_bp = Blueprint('insurance', __name__)

@insurance_bp.route('/insurance')
def page():
    return render_template('pages/insurance.html')

@insurance_bp.route('/api/insurance', methods=['GET'])
def api_list():
    return InsuranceController.get_policies()
