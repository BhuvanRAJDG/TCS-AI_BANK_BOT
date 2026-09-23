from datetime import datetime
from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, String, Enum as SAEnum
from sqlalchemy.orm import relationship

from .. import db


class Insurance(db.Model):
    __tablename__ = 'insurance_policies'
    __table_args__ = (
        db.Index('ix_insurance_customer_id', 'customer_id'),
        db.Index('ix_insurance_status',      'status'),
    )

    id              = Column(Integer, primary_key=True)
    customer_id     = Column(Integer, ForeignKey('customers.id'), nullable=False)
    policy_number   = Column(String(30), unique=True, nullable=False)
    policy_type     = Column(SAEnum('life','health','vehicle','property','travel',
                                    name='insurance_type'), nullable=False)
    provider        = Column(String(100), nullable=False)
    sum_assured     = Column(Float, nullable=False)
    premium_amount  = Column(Float, nullable=False)
    premium_frequency = Column(SAEnum('monthly','quarterly','annually',
                                      name='premium_freq'), default='annually')
    start_date      = Column(Date, nullable=False)
    end_date        = Column(Date, nullable=False)
    status          = Column(SAEnum('active','expired','cancelled','lapsed',
                                    name='insurance_status'), default='active')
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship('CustomerProfile', back_populates='insurance_policies')

    def __repr__(self):
        return f"<Insurance {self.policy_number} ({self.policy_type})>"
