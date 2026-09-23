"""
app/services/expense_split_service.py
Service for managing group bill splitting & shared expenses.
"""
from datetime import datetime
from app import db
from app.models.expense_split import ExpenseSplit, ExpenseSplitParticipant
from app.models.customer import CustomerProfile


def get_user_splits(customer_id: int) -> dict:
    """Return active and settled expense splits for the given customer."""
    # Find all splits where customer is initiator OR participant
    participant_splits = ExpenseSplitParticipant.query.filter_by(customer_id=customer_id).all()
    split_ids = {p.split_id for p in participant_splits}

    initiated_splits = ExpenseSplit.query.filter_by(initiator_customer_id=customer_id).all()
    for s in initiated_splits:
        split_ids.add(s.id)

    splits = ExpenseSplit.query.filter(ExpenseSplit.id.in_(split_ids)).order_by(ExpenseSplit.created_at.desc()).all()

    result = []
    total_owed_to_user = 0.0
    total_user_owes = 0.0

    for s in splits:
        participants_data = []
        user_participant = None

        for p in s.participants:
            c = p.customer
            p_name = c.name if c else f"Customer #{p.customer_id}"
            if p.customer_id == customer_id:
                user_participant = p

            participants_data.append({
                'id': p.id,
                'customer_id': p.customer_id,
                'name': p_name,
                'share_amount': p.share_amount,
                'paid': p.paid,
                'paid_at': p.paid_at.strftime('%Y-%m-%d %H:%M') if p.paid_at else None
            })

            # Calculate balances
            if s.initiator_customer_id == customer_id and p.customer_id != customer_id and not p.paid:
                total_owed_to_user += p.share_amount
            elif s.initiator_customer_id != customer_id and p.customer_id == customer_id and not p.paid:
                total_user_owes += p.share_amount

        result.append({
            'id': s.id,
            'title': s.title,
            'description': s.description or '',
            'total_amount': s.total_amount,
            'currency': s.currency,
            'status': s.status,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'initiator_name': s.initiator.name if s.initiator else 'Unknown',
            'is_initiator': s.initiator_customer_id == customer_id,
            'user_paid': user_participant.paid if user_participant else False,
            'user_share': user_participant.share_amount if user_participant else 0.0,
            'participants': participants_data
        })

    return {
        'splits': result,
        'summary': {
            'total_owed_to_you': round(total_owed_to_user, 2),
            'total_you_owe': round(total_user_owes, 2),
            'net_balance': round(total_owed_to_user - total_user_owes, 2)
        }
    }


def create_split(initiator_customer_id: int, title: str, total_amount: float,
                 description: str = '', participant_names: list[str] = None) -> dict:
    """Create a new expense split and add participants."""
    if not title or total_amount <= 0:
        raise ValueError("Title and positive total amount are required.")

    split = ExpenseSplit(
        initiator_customer_id=initiator_customer_id,
        title=title,
        description=description,
        total_amount=total_amount,
        status='open'
    )
    db.session.add(split)
    db.session.flush()

    # Find matching customers or default to other sample customers
    available_customers = CustomerProfile.query.all()
    selected_customers = [c for c in available_customers if c.id == initiator_customer_id]

    if participant_names:
        for name in participant_names:
            name_clean = name.strip().lower()
            matched = [c for c in available_customers if name_clean in c.name.lower() or name_clean in (c.user.email if c.user else '').lower()]
            if matched and matched[0] not in selected_customers:
                selected_customers.append(matched[0])

    # If fewer than 2 participants, pick 2 other random customers for demo
    if len(selected_customers) < 2:
        for c in available_customers:
            if c not in selected_customers:
                selected_customers.append(c)
                if len(selected_customers) >= 3:
                    break

    share = round(total_amount / len(selected_customers), 2)

    for c in selected_customers:
        is_initiator = (c.id == initiator_customer_id)
        p = ExpenseSplitParticipant(
            split_id=split.id,
            customer_id=c.id,
            share_amount=share,
            paid=is_initiator,
            paid_at=datetime.utcnow() if is_initiator else None
        )
        db.session.add(p)

    db.session.commit()
    return {'message': 'Expense split created successfully', 'split_id': split.id}


def settle_participant(split_id: int, customer_id: int) -> dict:
    """Mark a participant share as paid in an expense split."""
    participant = ExpenseSplitParticipant.query.filter_by(split_id=split_id, customer_id=customer_id).first()
    if not participant:
        raise ValueError("Participant record not found.")

    participant.paid = True
    participant.paid_at = datetime.utcnow()

    # Check if all participants have paid
    split = ExpenseSplit.query.get(split_id)
    if split:
        all_paid = all(p.paid for p in split.participants)
        if all_paid:
            split.status = 'settled'
        else:
            split.status = 'partially_settled'

    db.session.commit()
    return {'message': 'Share settled successfully'}
