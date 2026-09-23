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

    @staticmethod
    def process_transfer(sender_customer_id: int, recipient_name_or_target: str,
                         amount: float, remark: str = 'CSB Bot Transfer') -> dict:
        """
        Process a real-time money transfer between accounts or to external merchant/friend.
        Updates Account balance, creates Transaction record, logs AuditLog, and commits to DB.
        """
        import uuid
        from datetime import datetime
        from app.models.customer import CustomerProfile

        sender_account = Account.query.filter_by(customer_id=sender_customer_id, is_active=True).first()
        if not sender_account:
            raise ValueError("Sender has no active bank account.")

        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero.")

        if sender_account.balance < amount:
            raise ValueError(f"Insufficient account balance. Available: ₹{sender_account.balance:,.2f}")

        # Try to find target customer by name or email
        target_name = recipient_name_or_target.strip()
        recipient_account = None
        recipient_profile = CustomerProfile.query.filter(
            (CustomerProfile.name.ilike(f"%{target_name}%")) |
            (CustomerProfile.phone.ilike(f"%{target_name}%"))
        ).first()

        if recipient_profile:
            recipient_account = Account.query.filter_by(customer_id=recipient_profile.id, is_active=True).first()
            target_display_name = recipient_profile.name
        else:
            target_display_name = target_name

        # 1. Deduct money from sender
        sender_account.balance -= amount
        db.session.flush()

        ref_id = "UPI" + uuid.uuid4().hex[:10].upper()

        # 2. Create sender debit transaction
        sender_tx = Transaction(
            account_id=sender_account.id,
            amount=amount,
            transaction_type='debit',
            description=f"Transfer to {target_display_name} ({remark})",
            category='transfer',
            reference_id=ref_id,
            merchant=target_display_name,
            channel='upi',
            timestamp=datetime.utcnow(),
            balance_after=sender_account.balance
        )
        db.session.add(sender_tx)

        # 3. Credit recipient if internal account
        if recipient_account:
            recipient_account.balance += amount
            db.session.flush()

            ref_id_rcp = "UPI" + uuid.uuid4().hex[:10].upper()
            recipient_tx = Transaction(
                account_id=recipient_account.id,
                amount=amount,
                transaction_type='credit',
                description=f"Received from CSB User ({remark})",
                category='transfer',
                reference_id=ref_id_rcp,
                merchant="CSB Transfer",
                channel='upi',
                timestamp=datetime.utcnow(),
                balance_after=recipient_account.balance
            )
            db.session.add(recipient_tx)

        db.session.commit()

        return {
            'status': 'success',
            'reference_id': ref_id,
            'recipient': target_display_name,
            'amount': amount,
            'sender_account_number': sender_account.account_number,
            'new_balance': sender_account.balance,
            'timestamp': sender_tx.timestamp.strftime("%d %b %Y, %H:%M:%S")
        }

