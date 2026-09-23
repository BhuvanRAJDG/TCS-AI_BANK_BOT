"""
app/services/notification_service.py
"""
from app import db
from app.models import Notification


class NotificationService:
    @staticmethod
    def get_user_notifications(user_id, limit=20):
        notes = Notification.query.filter_by(user_id=user_id).order_by(
            Notification.created_at.desc()).limit(limit).all()
        return [{
            'id':         n.id,
            'title':      n.title,
            'message':    n.body,
            'type':       n.notif_type,
            'is_read':    n.is_read,
            'created_at': n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ''
        } for n in notes]

    @staticmethod
    def mark_as_read(user_id, notification_id):
        from datetime import datetime
        n = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if n:
            n.is_read  = True
            n.read_at  = datetime.utcnow()
            db.session.commit()
            return True
        return False
