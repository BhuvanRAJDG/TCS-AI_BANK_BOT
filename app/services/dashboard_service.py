"""
app/services/dashboard_service.py
Service layer for dashboard metrics.
Uses correct field names matching actual SQLAlchemy models.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import Account, Transaction, CreditScore, Loan, EMI, Autopay, FraudLog, Notification


class DashboardService:
    @staticmethod
    def get_dashboard_summary(customer_id: int) -> dict:
        # ── Accounts ─────────────────────────────────────────────────────────
        accounts    = Account.query.filter_by(customer_id=customer_id, is_active=True).all()
        account_ids = [a.id for a in accounts]

        current_balance = sum(a.balance for a in accounts if a.account_type != 'savings')
        total_savings   = sum(a.balance for a in accounts if a.account_type == 'savings')

        # ── Monthly income / spending (current month) ─────────────────────
        now            = datetime.utcnow()
        first_of_month = datetime(now.year, now.month, 1)

        monthly_spending = 0.0
        monthly_income   = 0.0

        if account_ids:
            debit_q = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'debit',
                Transaction.timestamp >= first_of_month
            ).scalar()
            monthly_spending = float(debit_q or 0)

            credit_q = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'credit',
                Transaction.timestamp >= first_of_month
            ).scalar()
            monthly_income = float(credit_q or 0)

        # ── 6-Month chart data ────────────────────────────────────────────
        labels, income_data, expense_data = [], [], []
        for i in range(5, -1, -1):
            m_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            m_end   = (m_start.replace(month=m_start.month % 12 + 1, day=1)
                       if m_start.month < 12 else m_start.replace(year=m_start.year + 1, month=1, day=1))
            labels.append(m_start.strftime("%b"))

            if account_ids:
                inc = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.account_id.in_(account_ids),
                    Transaction.transaction_type == 'credit',
                    Transaction.timestamp >= m_start,
                    Transaction.timestamp < m_end
                ).scalar() or 0.0
                exp = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.account_id.in_(account_ids),
                    Transaction.transaction_type == 'debit',
                    Transaction.timestamp >= m_start,
                    Transaction.timestamp < m_end
                ).scalar() or 0.0
            else:
                inc, exp = 0.0, 0.0

            income_data.append(float(inc))
            expense_data.append(float(exp))

        # ── Credit score ──────────────────────────────────────────────────
        cs = CreditScore.query.filter_by(customer_id=customer_id).order_by(
            CreditScore.recorded_at.desc()).first()
        credit_score  = cs.score if cs else 750
        credit_rating = cs.bureau if cs else 'CIBIL'

        # ── Loans / EMI progress ──────────────────────────────────────────
        loans = Loan.query.filter_by(customer_id=customer_id, status='active').all()
        loan_ids = [l.id for l in loans]
        total_loan_amount, total_paid = 0.0, 0.0
        upcoming_emis = []
        for loan in loans:
            total_loan_amount += float(loan.loan_amount or 0)
            paid = db.session.query(func.sum(EMI.paid_amount)).filter(
                EMI.loan_id == loan.id, EMI.status == 'paid'
            ).scalar() or 0.0
            total_paid += float(paid)
            next_emi = EMI.query.filter_by(loan_id=loan.id, status='pending').order_by(
                EMI.due_date.asc()).first()
            if next_emi:
                upcoming_emis.append({
                    'loan_type':  loan.loan_type,
                    'amount':     float(next_emi.total_amount or 0),
                    'due_date':   next_emi.due_date.strftime("%Y-%m-%d") if next_emi.due_date else None
                })

        emi_pct = round((total_paid / total_loan_amount * 100), 1) if total_loan_amount else 100.0

        # ── Autopay / upcoming bills ──────────────────────────────────────
        if account_ids:
            autopays = Autopay.query.filter(
                Autopay.account_id.in_(account_ids),
                Autopay.status == 'active'
            ).limit(5).all()
            upcoming_bills = [{
                'biller_name':  a.payee_name,
                'amount':       float(a.amount or 0),
                'next_execution': a.next_payment_date.strftime("%Y-%m-%d") if a.next_payment_date else 'N/A'
            } for a in autopays]
        else:
            upcoming_bills = []

        # ── Fraud count ───────────────────────────────────────────────────
        fraud_count = FraudLog.query.filter_by(
            customer_id=customer_id, status='flagged').count()

        # ── Recent transactions ───────────────────────────────────────────
        recent_txs = []
        if account_ids:
            txs = Transaction.query.filter(
                Transaction.account_id.in_(account_ids)
            ).order_by(Transaction.timestamp.desc()).limit(7).all()
            recent_txs = [{
                'id':        tx.id,
                'merchant':  tx.merchant or tx.description or 'Transfer',
                'category':  tx.category,
                'amount':    float(tx.amount or 0),
                'tx_type':   tx.transaction_type,
                'timestamp': tx.timestamp.strftime("%b %d, %H:%M") if tx.timestamp else '',
                'status':    'completed'
            } for tx in txs]

        return {
            'total_balance':       current_balance + total_savings,
            'current_balance':     current_balance,
            'total_savings':       total_savings,
            'monthly_spending':    monthly_spending,
            'monthly_income':      monthly_income,
            'chart_data':          {'labels': labels, 'income': income_data, 'expenses': expense_data},
            'credit_score':        credit_score,
            'credit_rating':       credit_rating,
            'emi_progress_pct':    emi_pct,
            'upcoming_emis':       upcoming_emis,
            'upcoming_bills':      upcoming_bills,
            'fraud_indicator_count': fraud_count,
            'recent_transactions': recent_txs,
            'ai_insights': [
                f"Your credit score is {credit_score}. Keeping utilization below 30% maintains this level.",
                f"You have {len(upcoming_emis)} EMIs due totaling ₹{sum(e['amount'] for e in upcoming_emis):,.2f}.",
                "Consider transferring surplus to your Savings account to earn higher interest."
            ]
        }
