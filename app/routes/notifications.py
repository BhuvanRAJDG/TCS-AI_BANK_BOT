"""
app/routes/notifications.py
"""
from flask import Blueprint, render_template, jsonify, g
from app.services.notification_service import NotificationService

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
def page():
    return render_template('pages/notifications.html')


@notifications_bp.route('/api/notifications', methods=['GET'])
def api_list():
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    notes = NotificationService.get_user_notifications(user.id)
    return jsonify({'status': 'success', 'data': notes}), 200


@notifications_bp.route('/api/notifications/<int:note_id>/read', methods=['POST'])
def api_read(note_id):
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    NotificationService.mark_as_read(user.id, note_id)
    return jsonify({'status': 'success'}), 200
