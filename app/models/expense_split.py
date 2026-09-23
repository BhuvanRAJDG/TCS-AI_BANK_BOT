from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class ExpenseSplit(db.Model):
    """Group expense / bill split between multiple customers."""
    __tablename__ = 'expense_splits'
    __table_args__ = (
        db.Index('ix_expense_splits_initiator', 'initiator_customer_id'),
        db.Index('ix_expense_splits_status',    'status'),
    )

    id                   = Column(Integer, primary_key=True)
    initiator_customer_id= Column(Integer, ForeignKey('customers.id'), nullable=False)
    title                = Column(String(200), nullable=False)
    description          = Column(Text, nullable=True)
    total_amount         = Column(Float, nullable=False)
    currency             = Column(String(10), default='INR')
    status               = Column(SAEnum('open','settled','partially_settled',
                                         name='split_status'), default='open')
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    initiator  = relationship('CustomerProfile', back_populates='expense_splits_initiated',
                               foreign_keys=[initiator_customer_id])
    participants = relationship('ExpenseSplitParticipant', back_populates='split',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ExpenseSplit '{self.title}' ₹{self.total_amount}>"


class ExpenseSplitParticipant(db.Model):
    __tablename__ = 'expense_split_participants'
    __table_args__ = (
        db.Index('ix_esp_split_id',    'split_id'),
        db.Index('ix_esp_customer_id', 'customer_id'),
    )

    id          = Column(Integer, primary_key=True)
    split_id    = Column(Integer, ForeignKey('expense_splits.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    share_amount= Column(Float, nullable=False)
    paid        = Column(db.Boolean, default=False)
    paid_at     = Column(DateTime, nullable=True)

    split    = relationship('ExpenseSplit', back_populates='participants')
    customer = relationship('CustomerProfile', back_populates='expense_split_participations')

    def __repr__(self):
        return f"<Participant split={self.split_id} customer={self.customer_id} paid={self.paid}>"
