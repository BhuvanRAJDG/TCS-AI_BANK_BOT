"""
smoke_test_all.py
End-to-end verification script for SentinelBank AI.
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.config import Config
from app.models import User, CustomerProfile, Account, Transaction, Loan, EMI, CreditScore

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'

def run_tests():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        print("[OK] Database tables created successfully.")

        # 1. Create seed user and profile
        user = User(email="test@sentinelbank.com", password_hash="hashed_pw",
                     role="customer", is_active=True, mfa_enabled=False)
        db.session.add(user)
        db.session.commit()

        customer = CustomerProfile(
            user_id=user.id,
            name="Anita Sharma",
            pan_masked="ABCDE1234F",
            aadhaar_masked="1234-5678-9012",
            phone="9876543210",
            city="Mumbai",
            state="Maharashtra",
            kyc_status="verified"
        )
        db.session.add(customer)
        db.session.commit()

        # 2. Add an account and transaction
        account = Account(
            customer_id=customer.id,
            account_number="1000998877",
            account_type="savings",
            balance=154320.50,
            currency="INR",
            ifsc_code="SENT0001001",
            is_active=True
        )
        db.session.add(account)
        db.session.commit()

        tx = Transaction(
            account_id=account.id,
            transaction_type="debit",
            amount=2500.00,
            merchant="Amazon India",
            category="shopping"
        )
        db.session.add(tx)
        db.session.commit()
        print("[OK] Seed data populated.")

        client = app.test_client()

        # 3. Test HTML page routes
        pages = ['/login', '/register', '/otp', '/dashboard', '/transactions',
                 '/loans', '/insurance', '/profile', '/notifications', '/chat']
        for page in pages:
            res = client.get(page)
            assert res.status_code in [200, 302], \
                f"Page {page} failed with status {res.status_code}"
            print(f"  GET {page} -> {res.status_code}")
        print("[OK] All page routes returned HTTP 200/302.")

        # 4. Test health endpoint
        res = client.get('/health')
        assert res.status_code == 200
        print("[OK] /health endpoint OK.")

        # 5. Test Chat API with JWT
        from app.security.jwt import create_access_token
        token = create_access_token(user_id=user.id, role=user.role)

        res = client.post('/api/chat',
                          headers={'Authorization': f'Bearer {token}'},
                          json={'message': 'What is my current account balance?'})
        print(f"  POST /api/chat -> {res.status_code}")
        data = res.get_json()
        print(f"  Response: {data}")
        assert res.status_code == 200
        assert "response" in data
        assert "latency_ms" in data
        print("[OK] /api/chat endpoint tested successfully.")

        print("\n=== ALL SMOKE TESTS PASSED ===")

if __name__ == '__main__':
    run_tests()
