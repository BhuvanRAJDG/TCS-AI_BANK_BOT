from datetime import datetime
from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, String, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class Autopay(db.Model):
    """Standing instruction / autopay mandate for recurring payments."""
    __tablename__ = 'autopays'
    __table_args__ = (
        db.Index('ix_autopays_account_id', 'account_id'),
        db.Index('ix_autopays_status',     'status'),
    )

    id              = Column(Integer, primary_key=True)
    account_id      = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    payee_name      = Column(String(200), nullable=False)
    payee_account   = Column(String(30), nullable=True)    # destination account/UPI
    amount          = Column(Float, nullable=False)
    frequency       = Column(SAEnum('daily','weekly','monthly','quarterly','annually',
                                    name='autopay_freq'), default='monthly')
    next_payment_date = Column(Date, nullable=False)
    end_date        = Column(Date, nullable=True)
    status          = Column(SAEnum('active','paused','cancelled',
                                    name='autopay_status'), default='active')
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account      = relationship('Account', back_populates='autopays')
    transactions = relationship('Transaction', back_populates='autopay')

    def __repr__(self):
        return f"<Autopay '{self.payee_name}' ₹{self.amount}/{self.frequency}>"
