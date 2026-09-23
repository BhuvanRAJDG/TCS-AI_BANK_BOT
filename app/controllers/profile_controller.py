"""
app/controllers/profile_controller.py
"""
from flask import request, jsonify, g
from app.services.profile_service import ProfileService


class ProfileController:
    @staticmethod
    def get_profile():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        return jsonify({'status': 'success', 'data': ProfileService.get_profile(user.id)}), 200

    @staticmethod
    def update_settings():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        req      = request.get_json() or {}
        success  = ProfileService.update_settings(
            user.id, language=req.get('language'), mfa_enabled=req.get('mfa_enabled'))
        if success:
            return jsonify({'status': 'success', 'message': 'Settings updated'}), 200
        return jsonify({'error': 'Failed to update settings'}), 400
