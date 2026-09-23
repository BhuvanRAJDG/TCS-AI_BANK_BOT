"""
app/routes/profile.py
"""
from flask import Blueprint, render_template, jsonify
from app.controllers.profile_controller import ProfileController

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
def profile_page():
    return render_template('pages/profile.html')

@profile_bp.route('/settings')
def settings_page():
    return render_template('pages/settings.html')

@profile_bp.route('/expense-split')
def expense_split_page():
    return render_template('pages/expense_split.html')

@profile_bp.route('/autopay')
def autopay_page():
    return render_template('pages/autopay.html')

@profile_bp.route('/fraud-center')
def fraud_center_page():
    return render_template('pages/fraud_center.html')

@profile_bp.route('/api/profile', methods=['GET'])
def api_profile():
    return ProfileController.get_profile()

@profile_bp.route('/api/settings', methods=['POST'])
def api_update_settings():
    return ProfileController.update_settings()
