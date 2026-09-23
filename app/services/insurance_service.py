"""
app/services/insurance_service.py
"""
from app import db
from app.models import Insurance


class InsuranceService:
    @staticmethod
    def get_user_policies(customer_id):
        policies = Insurance.query.filter_by(customer_id=customer_id).order_by(
            Insurance.created_at.desc()).all()
        return [{
            'id':             p.id,
            'policy_number':  p.policy_number,
            'policy_type':    p.policy_type,
            'provider':       p.provider,
            'sum_insured':    float(p.sum_assured or 0),
            'premium_amount': float(p.premium_amount or 0),
            'frequency':      p.premium_frequency,
            'status':         p.status,
            'start_date':     p.start_date.strftime("%Y-%m-%d") if p.start_date else None,
            'end_date':       p.end_date.strftime("%Y-%m-%d") if p.end_date else None
        } for p in policies]
