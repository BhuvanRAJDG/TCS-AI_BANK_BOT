"""
app/controllers/dashboard_controller.py
"""
from flask import jsonify, g
from app.services.dashboard_service import DashboardService
from app.models import CustomerProfile


class DashboardController:
    @staticmethod
    def get_dashboard_data():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
        customer_id = customer.id if customer else 1

        summary = DashboardService.get_dashboard_summary(customer_id)
        return jsonify({'status': 'success', 'data': summary}), 200
