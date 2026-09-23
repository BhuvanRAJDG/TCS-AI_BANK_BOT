"""
app/routes/dashboard.py
"""
from flask import Blueprint, render_template, jsonify
from app.controllers.dashboard_controller import DashboardController

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def page():
    return render_template('pages/dashboard.html')

@dashboard_bp.route('/api/dashboard/summary', methods=['GET'])
def api_summary():
    return DashboardController.get_dashboard_data()
