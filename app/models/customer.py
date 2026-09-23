from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class LanguageEnum(str):
    EN = 'en'
    KN = 'kn'
    HI = 'hi'
    TA = 'ta'
    TE = 'te'
    MR = 'mr'
    BN = 'bn'
    GU = 'gu'
    PA = 'pa'


class CustomerProfile(db.Model):
    __tablename__ = 'customers'
    __table_args__ = (
        db.Index('ix_customers_user_id', 'user_id'),
    )

    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    name                = Column(String(255), nullable=False)
    phone               = Column(String(20),  nullable=True)
    preferred_language  = Column(SAEnum('en','kn','hi','ta','te','mr','bn','gu','pa',
                                        name='lang_pref'), default='en', nullable=False)
    address             = Column(Text, nullable=True)
    city                = Column(String(100), nullable=True)
    state               = Column(String(100), nullable=True)
    aadhaar_masked      = Column(String(20),  nullable=True)   # XXXX-XXXX-1234
    pan_masked          = Column(String(12),  nullable=True)   # ABCXXXX1234
    date_of_birth       = Column(db.Date, nullable=True)
    occupation          = Column(String(100), nullable=True)
    annual_income       = Column(Float, nullable=True)
    net_worth           = Column(Float, nullable=True)
    risk_profile        = Column(SAEnum('conservative','moderate','aggressive',
                                        name='risk_profile'), nullable=True)
    profile_image       = Column(String(255), nullable=True)
    kyc_status          = Column(SAEnum('pending','verified','rejected',
                                        name='kyc_status'), default='pending')
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    user                 = relationship('User',            back_populates='customer_profile')
    accounts             = relationship('Account',         back_populates='customer',       lazy='dynamic')
    loans                = relationship('Loan',            back_populates='customer',       lazy='dynamic')
    credit_scores        = relationship('CreditScore',     back_populates='customer',       lazy='dynamic')
    insurance_policies   = relationship('Insurance',       back_populates='customer',       lazy='dynamic')
    fraud_logs           = relationship('FraudLog',        back_populates='customer',       lazy='dynamic')
    expense_splits_initiated      = relationship('ExpenseSplit',
                                                  foreign_keys='ExpenseSplit.initiator_customer_id',
                                                  back_populates='initiator',  lazy='dynamic')
    expense_split_participations  = relationship('ExpenseSplitParticipant',
                                                  back_populates='customer',   lazy='dynamic')

    def __repr__(self):
        return f"<CustomerProfile {self.name}>"
