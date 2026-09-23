from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class Account(db.Model):
    __tablename__ = 'accounts'
    __table_args__ = (
        db.Index('ix_accounts_number',      'account_number'),
        db.Index('ix_accounts_customer_id', 'customer_id'),
    )

    id             = Column(Integer, primary_key=True)
    customer_id    = Column(Integer, ForeignKey('customers.id'), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    account_type   = Column(SAEnum('savings','current','salary','nri','fixed_deposit',
                                    name='account_type'), nullable=False, default='savings')
    balance        = Column(Float, default=0.0)
    currency       = Column(String(10), default='INR')
    ifsc_code      = Column(String(15), nullable=True)
    branch         = Column(String(100), nullable=True)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer     = relationship('CustomerProfile', back_populates='accounts')
    transactions = relationship('Transaction', back_populates='account', lazy='dynamic')
    autopays     = relationship('Autopay',     back_populates='account', lazy='dynamic')

    def __repr__(self):
        return f"<Account {self.account_number} ({self.account_type}) ₹{self.balance:.2f}>"
