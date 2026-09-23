from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class AuditLog(db.Model):
    """Immutable append-only log of all security-relevant actions."""
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index('ix_audit_logs_user_id',    'user_id'),
        db.Index('ix_audit_logs_action',     'action'),
        db.Index('ix_audit_logs_created_at', 'created_at'),
    )

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey('users.id'), nullable=True)   # nullable for anon events
    action      = Column(String(100), nullable=False)   # LOGIN, LOGOUT, TRANSFER, VIEW_STATEMENT …
    entity_type = Column(String(50),  nullable=True)    # User, Account, Transaction …
    entity_id   = Column(Integer,     nullable=True)
    ip_address  = Column(String(45),  nullable=True)    # IPv4 or IPv6
    user_agent  = Column(String(500), nullable=True)
    details     = Column(Text,        nullable=True)    # JSON string for extra context
    severity    = Column(SAEnum('info','warning','critical', name='audit_severity'),
                          default='info')
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship('User', back_populates='audit_logs')

    def __repr__(self):
        return f"<AuditLog user={self.user_id} action={self.action} at={self.created_at}>"
