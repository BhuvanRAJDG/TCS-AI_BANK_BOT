from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class Loan(db.Model):
    __tablename__ = 'loans'
    __table_args__ = (
        db.Index('ix_loans_customer_id', 'customer_id'),
        db.Index('ix_loans_status',      'status'),
    )

    id            = Column(Integer, primary_key=True)
    customer_id   = Column(Integer, ForeignKey('customers.id'), nullable=False)
    loan_type     = Column(SAEnum('home','personal','vehicle','education','gold','business',
                                   name='loan_type'), nullable=False, default='personal')
    loan_amount   = Column(Float, nullable=False)
    outstanding   = Column(Float, nullable=False)   # remaining principal
    interest_rate = Column(Float, nullable=False)   # annual %
    tenure_months = Column(Integer, nullable=False)
    start_date    = Column(Date, nullable=False)
    end_date      = Column(Date, nullable=False)
    status        = Column(SAEnum('active','closed','defaulted','npa',
                                   name='loan_status'), default='active', nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer     = relationship('CustomerProfile', back_populates='loans')
    emis         = relationship('EMI',         back_populates='loan',  lazy='dynamic')
    transactions = relationship('Transaction', back_populates='loan',  lazy='dynamic')

    def __repr__(self):
        return f"<Loan {self.id} {self.loan_type} ₹{self.loan_amount} ({self.status})>"
