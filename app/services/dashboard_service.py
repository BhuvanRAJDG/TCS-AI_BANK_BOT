"""
app/services/dashboard_service.py
Service layer for dashboard metrics with full dynamic transaction aggregation and live updates.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import Account, Transaction, CreditScore, Loan, EMI, Autopay, FraudLog, Notification


class DashboardService:
    @staticmethod
    def get_dashboard_summary(customer_id: int) -> dict:
        if not customer_id:
            return {
                'total_balance': 0.0,
                'current_balance': 0.0,
                'total_savings': 0.0,
                'monthly_spending': 0.0,
                'monthly_income': 0.0,
                'chart_data': {'labels': [], 'income': [], 'expenses': []},
                'category_breakdown': {},
                'credit_score': 750,
                'credit_rating': 'CIBIL',
                'emi_progress_pct': 100.0,
                'upcoming_emis': [],
                'upcoming_bills': [],
                'fraud_indicator_count': 0,
                'recent_transactions': [],
                'ai_insights': ["Welcome to CBS Bank. Your account is active."]
            }

        # ── Accounts ─────────────────────────────────────────────────────────
        accounts    = Account.query.filter_by(customer_id=customer_id, is_active=True).all()
        account_ids = [a.id for a in accounts]

        savings_accounts = [a for a in accounts if (a.account_type or '').lower() == 'savings']
        current_accounts = [a for a in accounts if (a.account_type or '').lower() != 'savings']

        total_savings   = sum(float(a.balance or 0) for a in savings_accounts)
        current_balance = sum(float(a.balance or 0) for a in current_accounts)
        total_net_balance = sum(float(a.balance or 0) for a in accounts)

        now            = datetime.utcnow()
        first_of_month = datetime(now.year, now.month, 1)

        monthly_spending = 0.0
        monthly_income   = 0.0
        category_breakdown = {}

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

            # Category breakdown for donut/breakdown charts
            cat_rows = db.session.query(
                Transaction.category,
                func.sum(Transaction.amount)
            ).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'debit'
            ).group_by(Transaction.category).all()
            for c, amt in cat_rows:
                category_breakdown[c or 'Other'] = round(float(amt or 0), 2)

        # ── 6-Month Flow Data for Chart.js ──────────────────────────────────
        labels, income_data, expense_data = [], [], []
        for i in range(5, -1, -1):
            m_year = now.year
            m_month = now.month - i
            while m_month <= 0:
                m_month += 12
                m_year -= 1

            m_start = datetime(m_year, m_month, 1)
            if m_month == 12:
                m_end = datetime(m_year + 1, 1, 1)
            else:
                m_end = datetime(m_year, m_month + 1, 1)

            labels.append(m_start.strftime('%b %Y'))

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

            income_data.append(round(float(inc), 2))
            expense_data.append(round(float(exp), 2))

        # ── Credit score ──────────────────────────────────────────────────
        cs = CreditScore.query.filter_by(customer_id=customer_id).order_by(
            CreditScore.recorded_at.desc()).first()
        credit_score  = cs.score if cs else 770
        credit_rating = cs.bureau if cs else 'CIBIL'

        # ── Loans / EMI progress ──────────────────────────────────────────
        loans = Loan.query.filter_by(customer_id=customer_id, status='active').all()
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
                    'due_date':   next_emi.due_date.strftime('%Y-%m-%d') if next_emi.due_date else None
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
                'next_execution': a.next_payment_date.strftime('%Y-%m-%d') if a.next_payment_date else 'N/A'
            } for a in autopays]
        else:
            upcoming_bills = []

        # ── Fraud count ───────────────────────────────────────────────────
        fraud_count = FraudLog.query.filter_by(
            customer_id=customer_id, status='flagged').count()

        # ── Recent transactions (Real-time) ──────────────────────────────
        recent_txs = []
        if account_ids:
            txs = Transaction.query.filter(
                Transaction.account_id.in_(account_ids)
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            recent_txs = [{
                'id':           tx.id,
                'reference_no': tx.reference_id or f'TXN{tx.id:06d}',
                'merchant':     tx.merchant or tx.description or 'CBS Transfer',
                'category':     tx.category or 'General',
                'amount':       float(tx.amount or 0),
                'tx_type':      tx.transaction_type,
                'timestamp':    tx.timestamp.strftime('%b %d, %Y • %H:%M') if tx.timestamp else '',
                'balance_after': float(tx.balance_after) if tx.balance_after is not None else None,
                'status':       'completed'
            } for tx in txs]

        # Dynamic AI insight based on live figures
        insights = []
        if total_net_balance > 0:
            insights.append(f'Active balance across accounts: ₹{total_net_balance:,.2f}')
        if monthly_spending > 0:
            insights.append(f'Current month spending: ₹{monthly_spending:,.2f}')
        else:
            insights.append('No spending recorded yet for this monthly cycle.')
        if monthly_income > 0:
            insights.append(f'Total income credited this month: ₹{monthly_income:,.2f}')

        return {
            'total_balance':         total_net_balance,
            'current_balance':       current_balance,
            'total_savings':         total_savings,
            'monthly_spending':      monthly_spending,
            'monthly_income':        monthly_income,
            'chart_data':            {'labels': labels, 'income': income_data, 'expenses': expense_data},
            'category_breakdown':    category_breakdown,
            'credit_score':          credit_score,
            'credit_rating':         credit_rating,
            'emi_progress_pct':      emi_pct,
            'upcoming_emis':         upcoming_emis,
            'upcoming_bills':        upcoming_bills,
            'fraud_indicator_count': fraud_count,
            'recent_transactions':   recent_txs,
            'ai_insights':           insights
        }