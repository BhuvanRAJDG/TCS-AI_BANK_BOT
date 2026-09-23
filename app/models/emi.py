from datetime import datetime
from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class EMIStatusEnum(str):
    PENDING  = 'pending'
    PAID     = 'paid'
    OVERDUE  = 'overdue'
    WAIVED   = 'waived'


class EMI(db.Model):
    __tablename__ = 'emis'
    __table_args__ = (
        db.Index('ix_emis_loan_id',    'loan_id'),
        db.Index('ix_emis_due_date',   'due_date'),
        db.Index('ix_emis_status',     'status'),
    )

    id            = Column(Integer, primary_key=True)
    loan_id       = Column(Integer, ForeignKey('loans.id'), nullable=False)
    installment_no= Column(Integer, nullable=False)          # 1-based
    due_date      = Column(Date,    nullable=False)
    principal     = Column(Float,   nullable=False)
    interest      = Column(Float,   nullable=False)
    total_amount  = Column(Float,   nullable=False)
    paid_amount   = Column(Float,   default=0.0)
    paid_date     = Column(Date,    nullable=True)
    status        = Column(SAEnum('pending','paid','overdue','waived',
                                  name='emi_status'), default='pending', nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    loan = relationship('Loan', back_populates='emis')

    def __repr__(self):
        return f"<EMI loan={self.loan_id} #{self.installment_no} {self.status}>"
