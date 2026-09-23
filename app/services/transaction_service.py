"""
app/services/transaction_service.py
"""
from app import db
from app.models import Account, Transaction


class TransactionService:
    @staticmethod
    def get_user_transactions(customer_id, page=1, per_page=15,
                              category=None, tx_type=None, search=None):
        accounts    = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.id for a in accounts]

        if not account_ids:
            return {'items': [], 'total': 0, 'pages': 0, 'current_page': 1}

        q = Transaction.query.filter(Transaction.account_id.in_(account_ids))

        if category:
            q = q.filter(Transaction.category == category)
        if tx_type:
            q = q.filter(Transaction.transaction_type == tx_type)
        if search:
            q = q.filter(
                (Transaction.merchant.ilike(f'%{search}%')) |
                (Transaction.description.ilike(f'%{search}%'))
            )

        q = q.order_by(Transaction.timestamp.desc())
        pg = q.paginate(page=page, per_page=per_page, error_out=False)

        items = [{
            'id':           tx.id,
            'reference_no': tx.reference_id,
            'merchant':     tx.merchant or tx.description or 'N/A',
            'category':     tx.category,
            'amount':       float(tx.amount or 0),
            'tx_type':      tx.transaction_type,
            'status':       'completed',
            'channel':      tx.channel,
            'timestamp':    tx.timestamp.strftime("%Y-%m-%d %H:%M:%S") if tx.timestamp else '',
            'location':     None
        } for tx in pg.items]

        return {'items': items, 'total': pg.total, 'pages': pg.pages, 'current_page': page}

    @staticmethod
    def get_transaction_detail(customer_id, tx_id):
        accounts    = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.id for a in accounts]

        tx = Transaction.query.filter(
            Transaction.id == tx_id,
            Transaction.account_id.in_(account_ids)
        ).first()
        if not tx:
            return None

        return {
            'id':           tx.id,
            'reference_no': tx.reference_id,
            'account_id':   tx.account_id,
            'amount':       float(tx.amount or 0),
            'tx_type':      tx.transaction_type,
            'category':     tx.category,
            'merchant':     tx.merchant,
            'description':  tx.description,
            'channel':      tx.channel,
            'status':       'completed',
            'timestamp':    tx.timestamp.strftime("%Y-%m-%d %H:%M:%S") if tx.timestamp else '',
            'location':     None,
            'risk_score':   None
        }
