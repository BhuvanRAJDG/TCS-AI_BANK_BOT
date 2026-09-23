from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from .. import db


class Session(db.Model):
    """Tracks active JWT refresh-token sessions per user."""
    __tablename__ = 'sessions'
    __table_args__ = (
        db.Index('ix_sessions_user_id',       'user_id'),
        db.Index('ix_sessions_refresh_token', 'refresh_token'),
        db.Index('ix_sessions_is_active',     'is_active'),
    )

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey('users.id'), nullable=False)
    refresh_token = Column(String(512), unique=True, nullable=False)
    device_info   = Column(Text, nullable=True)    # JSON: os, browser, device name
    ip_address    = Column(String(45), nullable=True)
    is_active     = Column(Boolean, default=True)
    expires_at    = Column(DateTime, nullable=False)
    revoked_at    = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='sessions')

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def revoke(self):
        self.is_active  = False
        self.revoked_at = datetime.utcnow()

    def __repr__(self):
        return f"<Session user={self.user_id} active={self.is_active}>"
