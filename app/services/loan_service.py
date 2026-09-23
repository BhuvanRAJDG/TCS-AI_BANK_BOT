"""
app/services/loan_service.py
"""
from app import db
from app.models import Loan, EMI, CreditScore


class LoanService:
    @staticmethod
    def get_user_loans(customer_id):
        loans = Loan.query.filter_by(customer_id=customer_id).order_by(Loan.created_at.desc()).all()
        result = []
        for loan in loans:
            emis       = EMI.query.filter_by(loan_id=loan.id).order_by(EMI.installment_no.asc()).all()
            paid_count = sum(1 for e in emis if e.status == 'paid')
            next_emi   = next((e for e in emis if e.status == 'pending'), None)

            result.append({
                'id':             loan.id,
                'loan_type':      loan.loan_type,
                'amount':         float(loan.loan_amount or 0),
                'outstanding':    float(loan.outstanding or 0),
                'interest_rate':  float(loan.interest_rate or 0),
                'tenure_months':  loan.tenure_months,
                'status':         loan.status,
                'start_date':     loan.start_date.strftime("%Y-%m-%d") if loan.start_date else None,
                'end_date':       loan.end_date.strftime("%Y-%m-%d") if loan.end_date else None,
                'paid_emis':      paid_count,
                'total_emis':     len(emis),
                'next_emi_date':  next_emi.due_date.strftime("%Y-%m-%d") if next_emi and next_emi.due_date else None,
                'next_emi_amount': float(next_emi.total_amount or 0) if next_emi else 0.0
            })
        return result

    @staticmethod
    def get_user_emis(customer_id):
        loans    = Loan.query.filter_by(customer_id=customer_id, status='active').all()
        loan_ids = [l.id for l in loans]
        if not loan_ids:
            return []

        emis = EMI.query.filter(EMI.loan_id.in_(loan_ids)).order_by(EMI.due_date.asc()).all()
        return [{
            'id':                  e.id,
            'loan_id':             e.loan_id,
            'installment_number':  e.installment_no,
            'amount':              float(e.total_amount or 0),
            'principal_component': float(e.principal or 0),
            'interest_component':  float(e.interest or 0),
            'due_date':            e.due_date.strftime("%Y-%m-%d") if e.due_date else None,
            'status':              e.status
        } for e in emis]

    @staticmethod
    def get_credit_score_details(customer_id):
        cs = CreditScore.query.filter_by(customer_id=customer_id).order_by(
            CreditScore.recorded_at.desc()).first()
        if not cs:
            return {
                'score': 750, 'rating': 'Good',
                'bureau': 'CIBIL',
                'remarks': 'N/A', 'updated_at': 'Recently'
            }
        return {
            'score':      cs.score,
            'rating':     'Excellent' if cs.score >= 780 else 'Good' if cs.score >= 700 else 'Fair',
            'bureau':     cs.bureau,
            'remarks':    cs.remarks,
            'updated_at': cs.recorded_at.strftime("%Y-%m-%d") if cs.recorded_at else 'Recently'
        }
