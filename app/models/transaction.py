from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class Transaction(db.Model):
    __tablename__ = 'transactions'
    __table_args__ = (
        db.Index('ix_transactions_account_id', 'account_id'),
        db.Index('ix_transactions_timestamp',  'timestamp'),
        db.Index('ix_transactions_category',   'category'),
    )

    id               = Column(Integer, primary_key=True)
    account_id       = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    amount           = Column(Float, nullable=False)
    transaction_type = Column(SAEnum('debit','credit', name='txn_type'), nullable=False)
    description      = Column(String(255), nullable=True)
    category         = Column(SAEnum('transfer','food','shopping','utilities','emi',
                                      'salary','investment','insurance','entertainment',
                                      'travel','health','education','other',
                                      name='txn_category'), default='other')
    reference_id     = Column(String(50),  nullable=True, unique=True)  # UPI/NEFT ref
    merchant         = Column(String(200), nullable=True)
    channel          = Column(SAEnum('upi','neft','rtgs','imps','atm','pos','online','auto',
                                      name='txn_channel'), default='online')
    timestamp        = Column(DateTime, default=datetime.utcnow, nullable=False)
    balance_after    = Column(Float, nullable=True)

    # optional FK to related entities
    loan_id          = Column(Integer, ForeignKey('loans.id'),    nullable=True)
    autopay_id       = Column(Integer, ForeignKey('autopays.id'), nullable=True)

    account   = relationship('Account',  back_populates='transactions')
    loan      = relationship('Loan',     back_populates='transactions')
    autopay   = relationship('Autopay',  back_populates='transactions')
    fraud_logs= relationship('FraudLog', back_populates='transaction')

    def __repr__(self):
        return f"<Transaction {self.id} {self.transaction_type} ₹{self.amount} [{self.category}]>"
