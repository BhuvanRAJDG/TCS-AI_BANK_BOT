from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .. import db


class CreditScore(db.Model):
    __tablename__ = 'credit_scores'
    __table_args__ = (
        db.Index('ix_credit_scores_customer_id', 'customer_id'),
        db.Index('ix_credit_scores_recorded_at', 'recorded_at'),
    )

    id           = Column(Integer, primary_key=True)
    customer_id  = Column(Integer, ForeignKey('customers.id'), nullable=False)
    score        = Column(Integer, nullable=False)   # 300 – 900
    bureau       = Column(db.String(50), default='CIBIL')  # CIBIL / Experian / CRIF
    remarks      = Column(Text, nullable=True)
    recorded_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    customer = relationship('CustomerProfile', back_populates='credit_scores')

    def __repr__(self):
        return f"<CreditScore customer={self.customer_id} score={self.score}>"
