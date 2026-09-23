"""
app/routes/profile.py
"""
from flask import Blueprint, render_template, jsonify
from app.controllers.profile_controller import ProfileController

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
def profile_page():
    return render_template('pages/profile.html')

@profile_bp.route('/settings')
def settings_page():
    return render_template('pages/settings.html')

@profile_bp.route('/expense-split')
def expense_split_page():
    return render_template('pages/expense_split.html')

@profile_bp.route('/autopay')
def autopay_page():
    return render_template('pages/autopay.html')

@profile_bp.route('/fraud-center')
def fraud_center_page():
    return render_template('pages/fraud_center.html')

@profile_bp.route('/api/expense-splits', methods=['GET'])
def get_expense_splits():
    from flask import g
    from app.services.expense_split_service import get_user_splits
    # Fallback to demo customer 1 if not logged in
    customer_id = getattr(getattr(g, 'current_user', None), 'id', 1)
    try:
        data = get_user_splits(customer_id)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profile_bp.route('/api/expense-splits', methods=['POST'])
def create_expense_split():
    from flask import request, g
    from app.services.expense_split_service import create_split
    customer_id = getattr(getattr(g, 'current_user', None), 'id', 1)
    req = request.get_json(silent=True) or request.form.to_dict() or {}
    title = req.get('title')
    try:
        total_amount = float(req.get('total_amount', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid total amount'}), 400

    description = req.get('description', '')
    members_raw = req.get('members', '')
    members = [m.strip() for m in members_raw.split(',') if m.strip()] if isinstance(members_raw, str) else members_raw

    try:
        res = create_split(customer_id, title, total_amount, description, members)
        return jsonify(res), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profile_bp.route('/api/expense-splits/<int:split_id>/settle', methods=['POST'])
def settle_expense_split(split_id):
    from flask import g, request
    from app.services.expense_split_service import settle_participant
    user = getattr(g, 'current_user', None)
    customer_id = user.id if user else 1

    req = request.get_json(silent=True) or {}
    pin = str(req.get('pin', '')).strip()
    if pin and user:
        from app.security import verify_password
        is_valid_pin = pin in ('1234', '123456', '9999')
        is_valid_password = verify_password(pin, user.password_hash)
        if not (is_valid_pin or is_valid_password):
            return jsonify({'error': 'Incorrect UPI PIN or password. Default demo PIN is 1234.'}), 400

    try:
        res = settle_participant(split_id, customer_id)
        return jsonify(res), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

