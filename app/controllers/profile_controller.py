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
    def set_upi_pin():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        req = request.get_json(silent=True) or request.form.to_dict() or {}
        password = req.get('password', '')
        new_pin = req.get('new_pin', '')

        try:
            res = ProfileService.set_or_reset_upi_pin(user.id, password, new_pin)
            return jsonify(res), 200
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as exc:
            return jsonify({'error': f'Failed to update UPI PIN: {str(exc)}'}), 500

    @staticmethod
    def change_password():
        user = getattr(g, 'current_user', None)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        req = request.get_json(silent=True) or request.form.to_dict() or {}
        current_password = req.get('current_password', '')
        new_password = req.get('new_password', '')

        try:
            res = ProfileService.change_password(user.id, current_password, new_password)
            return jsonify(res), 200
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as exc:
            return jsonify({'error': f'Failed to change password: {str(exc)}'}), 500

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