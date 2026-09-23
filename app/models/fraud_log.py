from datetime import datetime
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, String, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class FraudLog(db.Model):
    __tablename__ = 'fraud_logs'
    __table_args__ = (
        db.Index('ix_fraud_logs_transaction_id', 'transaction_id'),
        db.Index('ix_fraud_logs_customer_id',    'customer_id'),
        db.Index('ix_fraud_logs_status',         'status'),
        db.Index('ix_fraud_logs_created_at',     'created_at'),
    )

    id             = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    customer_id    = Column(Integer, ForeignKey('customers.id'),    nullable=False)
    rule_triggered = Column(String(100), nullable=False)    # e.g. LARGE_AMOUNT, GEO_ANOMALY
    risk_score     = Column(Float, nullable=False, default=0.0)   # 0.0 – 1.0
    description    = Column(Text, nullable=True)
    status         = Column(SAEnum('flagged','reviewed','false_positive','confirmed_fraud',
                                    name='fraud_status'), default='flagged')
    reviewed_by    = Column(Integer, ForeignKey('users.id'), nullable=True)
    reviewed_at    = Column(DateTime, nullable=True)
    is_blocked     = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    transaction  = relationship('Transaction',     back_populates='fraud_logs')
    customer     = relationship('CustomerProfile', back_populates='fraud_logs')
    reviewer     = relationship('User',            foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<FraudLog txn={self.transaction_id} rule={self.rule_triggered} score={self.risk_score:.2f}>"
