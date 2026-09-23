"""
app/routes/dashboard.py
"""
from flask import Blueprint, render_template, jsonify
from app.controllers.dashboard_controller import DashboardController

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def root_page():
    from flask import g, redirect
    if getattr(g, 'current_user', None):
        return redirect('/dashboard')
    return redirect('/login')

@dashboard_bp.route('/dashboard')
def dashboard_page():
    return render_template('pages/dashboard.html')

@dashboard_bp.route('/api/dashboard/summary', methods=['GET'])
def api_summary():
    return DashboardController.get_dashboard_data()
