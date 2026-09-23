from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class RoleEnum(str):
    CUSTOMER   = 'customer'
    BANK_AGENT = 'bank_agent'
    ADMIN      = 'admin'


class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('ix_users_email', 'email'),
    )

    id            = Column(Integer, primary_key=True)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone         = Column(String(20),  nullable=True)
    role          = Column(SAEnum('customer','bank_agent','admin', name='user_role'),
                           nullable=False, default='customer')
    mfa_enabled   = Column(Boolean, default=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    customer_profile  = db.relationship('CustomerProfile', back_populates='user', uselist=False)
    sessions          = db.relationship('Session',       back_populates='user', lazy='dynamic')
    audit_logs        = db.relationship('AuditLog',      back_populates='user', lazy='dynamic')
    notifications     = db.relationship('Notification',  back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
