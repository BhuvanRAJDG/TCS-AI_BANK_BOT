from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, String, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class Notification(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = (
        db.Index('ix_notifications_user_id',    'user_id'),
        db.Index('ix_notifications_is_read',    'is_read'),
        db.Index('ix_notifications_created_at', 'created_at'),
    )

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey('users.id'), nullable=False)
    title      = Column(String(200), nullable=False)
    body       = Column(Text, nullable=False)
    notif_type = Column(SAEnum('transaction','loan','security','system','fraud','otp',
                                name='notif_type'), default='system')
    channel    = Column(SAEnum('push','email','sms','in_app',
                                name='notif_channel'), default='in_app')
    is_read    = Column(Boolean, default=False)
    read_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='notifications')

    def __repr__(self):
        return f"<Notification user={self.user_id} '{self.title}' read={self.is_read}>"
