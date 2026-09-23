"""
seed/seed_database.py
Deterministic seed for SentinelBank AI.
Run once after the database has been created:
    python -m seed.seed_database
"""

import os
import sys
import random
import math
import string
import uuid
from datetime import date, datetime, timedelta

# ── make sure the project root is on sys.path ────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import (
    User, CustomerProfile, Account, Loan, EMI, Transaction,
    CreditScore, Insurance, Autopay, Notification, FraudLog, AuditLog, Session
)
from app.models.expense_split import ExpenseSplit, ExpenseSplitParticipant

import bcrypt

# ── seed configuration ───────────────────────────────────────────────────────
RANDOM_SEED          = 42
NUM_CUSTOMERS        = 25
NUM_TRANSACTIONS     = 1100   # ≥ 1000
NUM_LOANS            = 15
ADMIN_EMAIL          = 'admin@example.com'
ADMIN_PASSWORD       = 'AdminPass123!'

random.seed(RANDOM_SEED)

# ── helper utilities ─────────────────────────────────────────────────────────

def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def mask_aadhaar(n: str) -> str:
    return f"XXXX-XXXX-{n[-4:]}"


def mask_pan(pan: str) -> str:
    return f"{pan[:3]}XXXXX{pan[-4:]}"


def rand_account_number() -> str:
    return ''.join(random.choices(string.digits, k=12))


def rand_ifsc() -> str:
    banks = ['SBIN', 'HDFC', 'ICIC', 'AXIS', 'KKBK', 'UTIB', 'PUNB', 'CNRB']
    return f"{random.choice(banks)}0{random.randint(100000, 999999)}"


def rand_policy_number() -> str:
    return f"POL{random.randint(10000000, 99999999)}"


def rand_reference() -> str:
    return uuid.uuid4().hex[:16].upper()


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def emi_schedule(principal: float, annual_rate: float, months: int, start: date):
    """Generate (installment_no, due_date, principal_part, interest_part, total) tuples."""
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        emi = principal / months
    else:
        emi = principal * monthly_rate * (1 + monthly_rate)**months / \
              ((1 + monthly_rate)**months - 1)
    balance = principal
    schedule = []
    for i in range(1, months + 1):
        interest_part  = balance * monthly_rate
        principal_part = emi - interest_part
        balance       -= principal_part
        due = date(start.year + (start.month + i - 1) // 12,
                   (start.month + i - 1) % 12 + 1, 1)
        schedule.append((i, due, round(principal_part, 2),
                         round(interest_part, 2), round(emi, 2)))
    return schedule


# ── fixture data ─────────────────────────────────────────────────────────────

CUSTOMER_DATA = [
    ('Aarav Sharma',      'aarav.sharma@example.com',      '9810001001', 'Delhi',       'Delhi',       'en', 'conservative', 'Software Engineer',  750000,   '123456781001', 'ABCS1234P001'),
    ('Priya Iyer',        'priya.iyer@example.com',        '9820001002', 'Chennai',     'Tamil Nadu',  'ta', 'moderate',     'Doctor',             1200000,  '234567892002', 'PRYI2345Q002'),
    ('Rohit Verma',       'rohit.verma@example.com',       '9830001003', 'Mumbai',      'Maharashtra', 'hi', 'aggressive',   'Entrepreneur',       2500000,  '345678903003', 'ROHV3456R003'),
    ('Ananya Reddy',      'ananya.reddy@example.com',      '9840001004', 'Hyderabad',   'Telangana',   'te', 'moderate',     'CA',                 900000,   '456789014004', 'ANAN4567S004'),
    ('Vikram Nair',       'vikram.nair@example.com',       '9850001005', 'Kochi',       'Kerala',      'en', 'conservative', 'Teacher',            480000,   '567890125005', 'VIKN5678T005'),
    ('Kavya Patel',       'kavya.patel@example.com',       '9860001006', 'Ahmedabad',   'Gujarat',     'gu', 'moderate',     'Architect',          780000,   '678901236006', 'KAVP6789U006'),
    ('Arjun Mehta',       'arjun.mehta@example.com',       '9870001007', 'Bangalore',   'Karnataka',   'kn', 'aggressive',   'Startup Founder',    3200000,  '789012347007', 'ARJM7890V007'),
    ('Sneha Desai',       'sneha.desai@example.com',       '9880001008', 'Surat',       'Gujarat',     'gu', 'conservative', 'Nurse',              360000,   '890123458008', 'SNED8901W008'),
    ('Karan Singh',       'karan.singh@example.com',       '9890001009', 'Chandigarh',  'Punjab',      'pa', 'moderate',     'Civil Servant',      650000,   '901234569009', 'KARS9012X009'),
    ('Meera Krishnan',    'meera.krishnan@example.com',    '9800001010', 'Mysore',      'Karnataka',   'kn', 'conservative', 'Homemaker',          200000,   '012345670010', 'MEEK0123Y010'),
    ('Aditya Gupta',      'aditya.gupta@example.com',      '9811001011', 'Lucknow',     'UP',          'hi', 'aggressive',   'Investment Banker',  4800000,  '112345671011', 'ADIG1234Z011'),
    ('Pooja Jain',        'pooja.jain@example.com',        '9821001012', 'Jaipur',      'Rajasthan',   'hi', 'moderate',     'Jeweller',           1500000,  '212345672012', 'POOJ2345A012'),
    ('Suresh Babu',       'suresh.babu@example.com',       '9831001013', 'Vizag',       'AP',          'te', 'conservative', 'Fisherman',          180000,   '312345673013', 'SURB3456B013'),
    ('Divya Pillai',      'divya.pillai@example.com',      '9841001014', 'Thiruvananthapuram', 'Kerala', 'en', 'moderate', 'Lawyer',              950000,   '412345674014', 'DIVP4567C014'),
    ('Rajeev Kumar',      'rajeev.kumar@example.com',      '9851001015', 'Patna',       'Bihar',       'hi', 'conservative', 'Farmer',             120000,   '512345675015', 'RAJK5678D015'),
    ('Neha Saxena',       'neha.saxena@example.com',       '9861001016', 'Bhopal',      'MP',          'hi', 'moderate',     'Pharmacist',         520000,   '612345676016', 'NEHS6789E016'),
    ('Girish Shetty',     'girish.shetty@example.com',     '9871001017', 'Mangalore',   'Karnataka',   'kn', 'aggressive',   'Hotel Owner',        2100000,  '712345677017', 'GIRS7890F017'),
    ('Lakshmi Rao',       'lakshmi.rao@example.com',       '9881001018', 'Pune',        'Maharashtra', 'mr', 'conservative', 'Retired',            300000,   '812345678018', 'LAKR8901G018'),
    ('Sachin Thakur',     'sachin.thakur@example.com',     '9891001019', 'Shimla',      'HP',          'hi', 'moderate',     'Tour Operator',      680000,   '912345679019', 'SACT9012H019'),
    ('Ritu Bose',         'ritu.bose@example.com',         '9801001020', 'Kolkata',     'WB',          'bn', 'aggressive',   'Fashion Designer',   1100000,  '013456780020', 'RITB0123I020'),
    ('Mahesh Pandey',     'mahesh.pandey@example.com',     '9812001021', 'Varanasi',    'UP',          'hi', 'conservative', 'Pandit',             90000,    '113456781021', 'MAHP1234J021'),
    ('Sunita Ghosh',      'sunita.ghosh@example.com',      '9822001022', 'Guwahati',    'Assam',       'en', 'moderate',     'NGO Worker',         340000,   '213456782022', 'SUNG2345K022'),
    ('Tarun Malhotra',    'tarun.malhotra@example.com',    '9832001023', 'Amritsar',    'Punjab',      'pa', 'aggressive',   'Real Estate Agent',  1800000,  '313456783023', 'TARM3456L023'),
    ('Asha Nambiar',      'asha.nambiar@example.com',      '9842001024', 'Kozhikode',   'Kerala',      'en', 'moderate',     'Principal',          600000,   '413456784024', 'ASHA4567M024'),
    ('Deepak Chaudhary',  'deepak.chaudhary@example.com',  '9852001025', 'Dehradun',    'Uttarakhand', 'hi', 'conservative', 'Army Officer',       840000,   '513456785025', 'DEPC5678N025'),
]

LOAN_TEMPLATES = [
    ('home',     7.5,  240),
    ('home',     8.0,  180),
    ('personal', 12.0,  36),
    ('personal', 14.5,  24),
    ('personal', 11.5,  48),
    ('vehicle',  9.0,   60),
    ('vehicle',  9.5,   48),
    ('education',8.5,  120),
    ('education',9.0,   84),
    ('gold',     7.0,   12),
    ('gold',     7.5,   18),
    ('business', 13.0,  60),
    ('business', 12.5,  36),
    ('home',     8.25, 300),
    ('personal', 15.0,  18),
]

INSURANCE_PROVIDERS = ['LIC India','Star Health','HDFC Ergo','ICICI Lombard',
                        'Bajaj Allianz','Max Bupa','Tata AIG','New India Assurance']

TXN_DESCRIPTIONS = {
    'food':          ['Swiggy Order','Zomato Delivery','Dominos Pizza','Hotel Stay','Chai Wala'],
    'shopping':      ['Flipkart Purchase','Amazon Order','Myntra Fashion','Croma Electronics','Reliance Trends'],
    'utilities':     ['Electricity Bill','Water Bill','Gas Cylinder','Internet Bill','Mobile Recharge'],
    'transfer':      ['NEFT to {name}','UPI to {name}','IMPS Transfer','RTGS Transfer'],
    'emi':           ['Loan EMI Payment','Home Loan EMI','Vehicle EMI','Education Loan EMI'],
    'salary':        ['Salary Credit','Monthly Salary','Performance Bonus'],
    'investment':    ['Mutual Fund SIP','Stock Purchase','RD Installment','PPF Deposit','NPS Contribution'],
    'insurance':     ['Premium Payment','Insurance Renewal','Life Insurance Premium'],
    'entertainment': ['Netflix Subscription','Amazon Prime','BookMyShow Tickets','Spotify'],
    'travel':        ['IRCTC Ticket','IndiGo Booking','Ola Cab','Rapido Ride','Petrol Station'],
    'health':        ['Apollo Pharmacy','Dr. Lal PathLabs','Hospital Bill','Max Healthcare'],
    'education':     ['Byju\'s Subscription','Coursera Payment','School Fees','Coaching Fees'],
    'other':         ['Miscellaneous','ATM Withdrawal','Bank Charges','Cheque Payment'],
}

CHANNELS = ['upi','neft','rtgs','imps','atm','pos','online','auto']
CHANNEL_WEIGHTS = [35,15,5,15,10,10,8,2]

# ── main seed function ────────────────────────────────────────────────────────

def seed():
    app = create_app()
    with app.app_context():
        print("⚠  Dropping and re-creating all tables …")
        db.drop_all()
        db.create_all()
        print("✓  Tables created.")

        today = date.today()

        # ── 1. Admin user ────────────────────────────────────────────────────
        admin = User(
            email         = ADMIN_EMAIL,
            password_hash = hash_pw(ADMIN_PASSWORD),
            role          = 'admin',
            mfa_enabled   = True,
            is_active     = True,
        )
        db.session.add(admin)
        db.session.flush()

        # ── 2. Customer users + profiles ─────────────────────────────────────
        users       = []
        customers   = []
        accounts_map = {}   # customer_id -> list[Account]

        for i, row in enumerate(CUSTOMER_DATA):
            (name, email, phone, city, state, lang, risk,
             occupation, income, aadhaar_raw, pan_raw) = row

            u = User(
                email         = email,
                password_hash = hash_pw('Pass@123!'),
                phone         = phone,
                role          = 'customer',
                mfa_enabled   = (i % 4 == 0),
                is_active     = True,
            )
            db.session.add(u)
            db.session.flush()

            dob = date(1970 + i, (i % 12) + 1, (i % 28) + 1)
            cp = CustomerProfile(
                user_id            = u.id,
                name               = name,
                phone              = phone,
                preferred_language = lang,
                address            = f"{i+1}, Street {i+1}, {city}",
                city               = city,
                state              = state,
                aadhaar_masked     = mask_aadhaar(aadhaar_raw),
                pan_masked         = mask_pan(pan_raw),
                date_of_birth      = dob,
                occupation         = occupation,
                annual_income      = float(income),
                net_worth          = float(income) * random.uniform(2, 8),
                risk_profile       = risk,
                kyc_status         = 'verified',
            )
            db.session.add(cp)
            db.session.flush()

            users.append(u)
            customers.append(cp)

            # ── 3. Bank accounts (each customer gets 1–2 accounts) ───────────
            n_accounts = 1 if i % 3 != 0 else 2
            acc_list = []
            for j in range(n_accounts):
                a_type = 'savings' if j == 0 else 'current'
                balance = round(random.uniform(5000, 500000), 2)
                acc = Account(
                    customer_id    = cp.id,
                    account_number = rand_account_number(),
                    account_type   = a_type,
                    balance        = balance,
                    ifsc_code      = rand_ifsc(),
                    branch         = f"{city} Main Branch",
                )
                db.session.add(acc)
                db.session.flush()
                acc_list.append(acc)
            accounts_map[cp.id] = acc_list

        db.session.flush()
        print(f"✓  {len(customers)} customers + {sum(len(v) for v in accounts_map.values())} accounts.")

        # ── 4. Loans + EMI schedules ─────────────────────────────────────────
        loans_created = []
        for li, (loan_type, rate, tenure) in enumerate(LOAN_TEMPLATES):
            cust = customers[li % NUM_CUSTOMERS]
            principal = round(random.uniform(50000, 5000000), -3)
            start = random_date(date(2021, 1, 1), date(2023, 12, 31))
            end   = date(start.year + tenure // 12, start.month + tenure % 12 or 12, 1)
            elapsed_months = min(tenure, max(0,
                (today.year - start.year) * 12 + (today.month - start.month)))
            monthly_rate = rate / 12 / 100
            emi_amt = (principal * monthly_rate * (1 + monthly_rate)**tenure /
                       ((1 + monthly_rate)**tenure - 1)) if monthly_rate else principal / tenure
            outstanding = principal - emi_amt * elapsed_months * 0.7   # approx
            outstanding = max(0, round(outstanding, 2))
            status = 'active' if outstanding > 0 else 'closed'

            loan = Loan(
                customer_id   = cust.id,
                loan_type     = loan_type,
                loan_amount   = principal,
                outstanding   = outstanding,
                interest_rate = rate,
                tenure_months = tenure,
                start_date    = start,
                end_date      = end,
                status        = status,
            )
            db.session.add(loan)
            db.session.flush()
            loans_created.append(loan)

            # Generate EMI rows
            schedule = emi_schedule(principal, rate, tenure, start)
            for (inst_no, due, princ_p, int_p, total) in schedule:
                paid_this = due < today
                emi_status = 'paid' if paid_this else (
                    'overdue' if (due + timedelta(days=30)) < today else 'pending'
                )
                emi_obj = EMI(
                    loan_id        = loan.id,
                    installment_no = inst_no,
                    due_date       = due,
                    principal      = princ_p,
                    interest       = int_p,
                    total_amount   = total,
                    paid_amount    = total if paid_this else 0.0,
                    paid_date      = due if paid_this else None,
                    status         = emi_status,
                )
                db.session.add(emi_obj)

        db.session.flush()
        print(f"✓  {NUM_LOANS} loans with EMI schedules.")

        # ── 5. Credit scores ─────────────────────────────────────────────────
        bureaus = ['CIBIL', 'Experian', 'CRIF']
        score_base = [720, 680, 760, 810, 650, 740, 790, 610, 700, 770,
                      830, 720, 580, 750, 640, 710, 800, 690, 730, 780,
                      650, 720, 760, 700, 810]
        for i, cust in enumerate(customers):
            for b in bureaus[:random.randint(1, 3)]:
                score_val = score_base[i] + random.randint(-20, 20)
                cs = CreditScore(
                    customer_id = cust.id,
                    score       = min(900, max(300, score_val)),
                    bureau      = b,
                    remarks     = f"Auto-generated on behalf of {cust.name}",
                    recorded_at = datetime.now() - timedelta(days=random.randint(1, 90)),
                )
                db.session.add(cs)

        db.session.flush()
        print("✓  Credit scores seeded.")

        # ── 6. Insurance policies ────────────────────────────────────────────
        ins_types = ['life','health','vehicle','property','travel']
        for i, cust in enumerate(customers[:20]):
            pol_type = ins_types[i % len(ins_types)]
            start_d  = random_date(date(2020, 1, 1), date(2023, 1, 1))
            end_d    = date(start_d.year + (3 if pol_type != 'travel' else 1),
                            start_d.month, start_d.day)
            ins = Insurance(
                customer_id       = cust.id,
                policy_number     = rand_policy_number(),
                policy_type       = pol_type,
                provider          = random.choice(INSURANCE_PROVIDERS),
                sum_assured       = round(random.uniform(500000, 10000000), -3),
                premium_amount    = round(random.uniform(5000, 50000), 2),
                premium_frequency = random.choice(['monthly','quarterly','annually']),
                start_date        = start_d,
                end_date          = end_d,
                status            = 'active' if end_d > today else 'expired',
            )
            db.session.add(ins)

        db.session.flush()
        print("✓  Insurance policies seeded.")

        # ── 7. Autopay mandates ──────────────────────────────────────────────
        payees = ['BESCOM Electricity','Jio Broadband','LIC Premium',
                  'HDFC Credit Card','Spotify India','Netflix India',
                  'SBI Car Loan EMI','Housing Society','Google One Storage']
        for i, cust in enumerate(customers[:18]):
            accs = accounts_map[cust.id]
            ap = Autopay(
                account_id        = accs[0].id,
                payee_name        = payees[i % len(payees)],
                payee_account     = rand_account_number(),
                amount            = round(random.uniform(199, 15000), 2),
                frequency         = random.choice(['monthly','quarterly']),
                next_payment_date = today + timedelta(days=random.randint(1, 30)),
                status            = 'active',
            )
            db.session.add(ap)

        db.session.flush()
        print("✓  Autopay mandates seeded.")

        # ── 8. Transactions (≥ 1000) ─────────────────────────────────────────
        categories = list(TXN_DESCRIPTIONS.keys())
        cat_weights = [5,15,10,12,8,5,8,5,5,8,5,5,9]

        # flat list of all accounts
        all_accounts = [acc for accs in accounts_map.values() for acc in accs]

        txns_created = []
        for ti in range(NUM_TRANSACTIONS):
            acc = random.choice(all_accounts)
            cat = random.choices(categories, weights=cat_weights, k=1)[0]
            t_type = 'credit' if cat == 'salary' else 'debit'
            if random.random() < 0.15:
                t_type = 'credit'   # misc credits
            amount = round(random.uniform(50, 50000), 2)
            desc_tpl = random.choice(TXN_DESCRIPTIONS[cat])
            cust_name = next((c.name for c in customers
                              if any(a.customer_id == c.id for a in all_accounts
                                     if a.id == acc.id)), 'Someone')
            description = desc_tpl.replace('{name}', cust_name)
            ts = datetime.now() - timedelta(days=random.randint(0, 730),
                                            hours=random.randint(0, 23),
                                            minutes=random.randint(0, 59))
            txn = Transaction(
                account_id       = acc.id,
                amount           = amount,
                transaction_type = t_type,
                description      = description,
                category         = cat,
                reference_id     = rand_reference(),
                channel          = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0],
                timestamp        = ts,
                balance_after    = round(acc.balance + (amount if t_type == 'credit' else -amount), 2),
            )
            db.session.add(txn)
            txns_created.append(txn)

        db.session.flush()
        print(f"✓  {NUM_TRANSACTIONS} transactions seeded.")

        # ── 9. Fraud logs (seed ~30 suspicious ones) ──────────────────────────
        fraud_rules = ['LARGE_AMOUNT','GEO_ANOMALY','RAPID_SUCCESSIVE',
                       'NIGHT_TRANSACTION','UNUSUAL_MERCHANT','VELOCITY_BREACH']
        for i in range(30):
            txn = txns_created[i * 36]   # spread evenly
            cust = customers[i % NUM_CUSTOMERS]
            fl = FraudLog(
                transaction_id = txn.id,
                customer_id    = cust.id,
                rule_triggered = fraud_rules[i % len(fraud_rules)],
                risk_score     = round(random.uniform(0.55, 0.99), 4),
                description    = f"Rule {fraud_rules[i % len(fraud_rules)]} triggered for txn {txn.id}",
                status         = random.choice(['flagged','reviewed','false_positive']),
                is_blocked     = (i % 10 == 0),
            )
            db.session.add(fl)

        db.session.flush()
        print("✓  Fraud logs seeded.")

        # ── 10. Notifications ─────────────────────────────────────────────────
        notif_templates = [
            ('Transaction Alert',       'Your account was debited ₹{amt}.',    'transaction'),
            ('EMI Due Reminder',        'Your EMI of ₹{amt} is due in 3 days.','loan'),
            ('Login from new device',   'A new login was detected.',            'security'),
            ('Credit Score Updated',    'Your CIBIL score has been updated.',   'system'),
            ('Suspicious Activity',     'Unusual activity detected on account.','fraud'),
        ]
        for i, u in enumerate(users):
            for j in range(random.randint(1, 5)):
                tmpl = notif_templates[(i + j) % len(notif_templates)]
                title, body_tpl, ntype = tmpl
                body = body_tpl.replace('{amt}', str(round(random.uniform(200, 20000), 2)))
                is_read = (j % 3 != 0)
                notif = Notification(
                    user_id    = u.id,
                    title      = title,
                    body       = body,
                    notif_type = ntype,
                    channel    = 'in_app',
                    is_read    = is_read,
                    read_at    = datetime.utcnow() if is_read else None,
                )
                db.session.add(notif)

        db.session.flush()
        print("✓  Notifications seeded.")

        # ── 11. Audit logs (sample) ───────────────────────────────────────────
        actions = ['LOGIN','LOGOUT','VIEW_STATEMENT','TRANSFER','CHANGE_PASSWORD',
                   'ENABLE_MFA','VIEW_LOAN','DOWNLOAD_STATEMENT']
        for i in range(80):
            u = random.choice(users)
            al = AuditLog(
                user_id     = u.id,
                action      = random.choice(actions),
                entity_type = random.choice(['Account','Transaction','User','Loan']),
                entity_id   = random.randint(1, 50),
                ip_address  = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}",
                user_agent  = 'Mozilla/5.0 (SentinelBank Seed)',
                details     = '{"seeded": true}',
                severity    = random.choice(['info','info','info','warning','critical']),
                created_at  = datetime.now() - timedelta(days=random.randint(0, 60)),
            )
            db.session.add(al)

        db.session.flush()
        print("✓  Audit logs seeded.")

        # ── 12. Expense splits ────────────────────────────────────────────────
        group_trips = [
            ('Goa Trip Expenses',    ['Aarav Sharma','Priya Iyer','Rohit Verma','Ananya Reddy'], 45000),
            ('Diwali Party',         ['Kavya Patel','Arjun Mehta','Sneha Desai'],                12000),
            ('Office Lunch Split',   ['Karan Singh','Meera Krishnan','Aditya Gupta'],            3500),
        ]
        name_to_customer = {c.name: c for c in customers}
        for title, members, total in group_trips:
            initiator = name_to_customer.get(members[0])
            if not initiator:
                continue
            es = ExpenseSplit(
                initiator_customer_id = initiator.id,
                title       = title,
                total_amount= total,
                status      = 'open',
            )
            db.session.add(es)
            db.session.flush()
            share = round(total / len(members), 2)
            for m_name in members:
                mc = name_to_customer.get(m_name)
                if mc:
                    esp = ExpenseSplitParticipant(
                        split_id     = es.id,
                        customer_id  = mc.id,
                        share_amount = share,
                        paid         = (m_name == members[0]),
                        paid_at      = datetime.utcnow() if m_name == members[0] else None,
                    )
                    db.session.add(esp)

        db.session.flush()
        print("✓  Expense splits seeded.")

        db.session.commit()
        print("\n🎉  Seeding complete!")
        print(f"   Admin → {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"   Customer accounts → email from list / password: Pass@123!")


if __name__ == '__main__':
    seed()
