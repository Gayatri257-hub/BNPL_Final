"""
SmartPay Demo Data Seeder
Run: python demo_data.py
Populates database with 50 realistic Indian users with full transaction history,
fraud patterns, BNPL plans, repayments and KYC records for demonstration.
"""
import os, sys, random
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app
from extensions import db, bcrypt
from models.user import User
from models.transaction import Transaction
from models.bnpl_plan import BNPLPlan
from models.repayment import Repayment
from models.fraud_log import FraudLog
from models.kyc import KYCRecord
from utils.encryption import encrypt_field, hash_for_lookup

app = create_app()

INDIAN_NAMES = [
    ("Arjun Sharma", "arjun.sharma"), ("Priya Patel", "priya.patel"),
    ("Rahul Gupta", "rahul.gupta"), ("Sneha Joshi", "sneha.joshi"),
    ("Vikram Singh", "vikram.singh"), ("Anjali Mehta", "anjali.mehta"),
    ("Rohan Desai", "rohan.desai"), ("Kavita Nair", "kavita.nair"),
    ("Aditya Kumar", "aditya.kumar"), ("Pooja Iyer", "pooja.iyer"),
    ("Sanjay Verma", "sanjay.verma"), ("Meera Reddy", "meera.reddy"),
    ("Rajesh Malhotra", "rajesh.malhotra"), ("Sunita Rao", "sunita.rao"),
    ("Deepak Jain", "deepak.jain"), ("Anita Pillai", "anita.pillai"),
    ("Suresh Agarwal", "suresh.agarwal"), ("Ritu Saxena", "ritu.saxena"),
    ("Manish Tiwari", "manish.tiwari"), ("Neha Bose", "neha.bose"),
    ("Amit Chopra", "amit.chopra"), ("Divya Menon", "divya.menon"),
    ("Karan Bajaj", "karan.bajaj"), ("Shreya Das", "shreya.das"),
    ("Nikhil Pandey", "nikhil.pandey"), ("Swati Bhatt", "swati.bhatt"),
    ("Gaurav Mishra", "gaurav.mishra"), ("Preeti Chauhan", "preeti.chauhan"),
    ("Varun Khanna", "varun.khanna"), ("Nisha Sinha", "nisha.sinha"),
    ("Harsh Aggarwal", "harsh.aggarwal"), ("Pallavi Shukla", "pallavi.shukla"),
    ("Mohit Bansal", "mohit.bansal"), ("Riya Kapoor", "riya.kapoor"),
    ("Siddharth Roy", "siddharth.roy"), ("Tanvi Ghosh", "tanvi.ghosh"),
    ("Akash Yadav", "akash.yadav"), ("Smita Patil", "smita.patil"),
    ("Rohit Kulkarni", "rohit.kulkarni"), ("Nidhi Dubey", "nidhi.dubey"),
    ("Vivek Oberoi", "vivek.oberoi"), ("Shweta Tripathi", "shweta.tripathi"),
    ("Nitin Rawat", "nitin.rawat"), ("Madhuri Deshpande", "madhuri.deshpande"),
    ("Sumit Kaur", "sumit.kaur"), ("Geeta Bhardwaj", "geeta.bhardwaj"),
    ("Tarun Srivastava", "tarun.srivastava"), ("Manju Goswami", "manju.goswami"),
    ("Pankaj Chaudhary", "pankaj.chaudhary"), ("Seema Naik", "seema.naik"),
]

INDIAN_CITIES = ["Pune", "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]

INCOME_RANGES = ["Below ₹15k", "₹15k-30k", "₹30k-60k", "₹60k-1L", "Above ₹1L"]
INCOME_VALUES = {"Below ₹15k": 12000, "₹15k-30k": 22000, "₹30k-60k": 45000, "₹60k-1L": 80000, "Above ₹1L": 150000}
# Credit limits derived from income (3x monthly income, capped at 1,00,000)
CREDIT_LIMITS = {"Below ₹15k": 15000, "₹15k-30k": 30000, "₹30k-60k": 60000, "₹60k-1L": 90000, "Above ₹1L": 100000}

PRODUCTS = [
    ("OnePlus Buds Pro", "Electronics", 4999),
    ("realme Smart TV 32\"", "Electronics", 15999),
    ("boAt Rockerz 450", "Electronics", 1299),
    ("JBL Flip 6 Speaker", "Electronics", 8499),
    ("Levi's Classic Jeans", "Fashion", 3499),
    ("Puma Running Shoes", "Fashion", 2799),
    ("Ray-Ban Aviators", "Fashion", 5499),
    ("Fossil Gen 6 Smartwatch", "Fashion", 12999),
    ("Atomic Habits", "Books", 499),
    ("Philips Air Purifier", "Home & Kitchen", 8999),
    ("Prestige Induction Cooktop", "Home & Kitchen", 2199),
    ("Nivia Football", "Sports", 699),
    ("Boldfit Yoga Mat", "Sports", 899),
    ("MI Smart Band 8", "Electronics", 2999),
    ("Nike Air Max Sneakers", "Fashion", 7999),
]

# PAN card patterns (fake but realistic format)
PAN_PATTERNS = [
    "ABCPS1234A", "XYZRS5678B", "MNOPQ9012C", "LMNTR3456D",
    "PQRST7890E", "UVWXY2345F", "ABCDE6789G", "FGHIJ0123H",
    "KLMNO4567I", "PQRST8901J", "UVWXA2345K", "BCDEF6789L",
    "GHIJK0123M", "LMNOP4567N", "QRSTU8901O", "VWXYA2345P",
    "BCDEG6789Q", "HIJKL0123R", "MNOPQ4567S", "RSTUV8901T",
]

def random_date(start_days_ago=365, end_days_ago=0):
    days = random.randint(end_days_ago, start_days_ago)
    return datetime.utcnow() - timedelta(days=days)

def seed_database():
    with app.app_context():
        print("=" * 60)
        print("SmartPay Demo Data Seeder")
        print("=" * 60)

        # Clear existing data
        print("Clearing existing demo data...")
        FraudLog.query.delete()
        Repayment.query.delete()
        BNPLPlan.query.delete()
        Transaction.query.delete()
        KYCRecord.query.delete()
        User.query.delete()
        db.session.commit()
        print("Cleared. Seeding fresh data...")

        users_created = []

        # Define user profiles: (name_idx, profile_type, credit_score, income_range, is_fraudster, is_defaulter, is_blacklisted)
        user_profiles = [
            # EXCELLENT users (10)
            (0, "excellent", 850, "Above ₹1L", False, False, False),
            (1, "excellent", 820, "₹60k-1L", False, False, False),
            (2, "excellent", 800, "₹60k-1L", False, False, False),
            (3, "excellent", 780, "Above ₹1L", False, False, False),
            (4, "excellent", 760, "₹30k-60k", False, False, False),
            (5, "excellent", 755, "₹60k-1L", False, False, False),
            (6, "excellent", 830, "Above ₹1L", False, False, False),
            (7, "excellent", 790, "₹60k-1L", False, False, False),
            (8, "excellent", 810, "Above ₹1L", False, False, False),
            (9, "excellent", 770, "₹30k-60k", False, False, False),
            # GOOD users (10)
            (10, "good", 720, "₹30k-60k", False, False, False),
            (11, "good", 700, "₹30k-60k", False, False, False),
            (12, "good", 690, "₹15k-30k", False, False, False),
            (13, "good", 680, "₹30k-60k", False, False, False),
            (14, "good", 710, "₹60k-1L", False, False, False),
            (15, "good", 695, "₹30k-60k", False, False, False),
            (16, "good", 730, "₹30k-60k", False, False, False),
            (17, "good", 715, "₹60k-1L", False, False, False),
            (18, "good", 705, "₹30k-60k", False, False, False),
            (19, "good", 725, "₹30k-60k", False, False, False),
            # FAIR users (10)
            (20, "fair", 620, "₹15k-30k", False, False, False),
            (21, "fair", 600, "₹15k-30k", False, True, False),
            (22, "fair", 580, "₹15k-30k", False, True, False),
            (23, "fair", 610, "₹30k-60k", False, False, False),
            (24, "fair", 590, "₹15k-30k", False, True, False),
            (25, "fair", 630, "₹15k-30k", False, False, False),
            (26, "fair", 605, "₹15k-30k", False, False, False),
            (27, "fair", 575, "Below ₹15k", False, True, False),
            (28, "fair", 615, "₹15k-30k", False, False, False),
            (29, "fair", 595, "₹15k-30k", False, True, False),
            # POOR/FRAUDULENT users (10)
            (30, "poor", 480, "Below ₹15k", False, True, False),
            (31, "poor", 450, "Below ₹15k", True, True, False),
            (32, "poor", 420, "Below ₹15k", True, True, True),
            (33, "poor", 400, "Below ₹15k", False, True, False),
            (34, "poor", 470, "₹15k-30k", True, True, True),
            (35, "poor", 390, "Below ₹15k", False, True, False),
            (36, "poor", 460, "Below ₹15k", True, False, False),
            (37, "poor", 430, "Below ₹15k", True, True, True),
            (38, "poor", 445, "Below ₹15k", False, True, False),
            (39, "poor", 410, "Below ₹15k", True, True, False),
            # MIXED (10)
            (40, "good", 740, "₹60k-1L", False, False, False),
            (41, "fair", 560, "₹15k-30k", False, False, False),
            (42, "good", 670, "₹30k-60k", False, False, False),
            (43, "poor", 490, "Below ₹15k", True, True, False),
            (44, "excellent", 840, "Above ₹1L", False, False, False),
            (45, "fair", 550, "₹15k-30k", False, True, False),
            (46, "good", 660, "₹30k-60k", False, False, False),
            (47, "poor", 440, "Below ₹15k", True, True, True),
            (48, "good", 685, "₹30k-60k", False, False, False),
            (49, "fair", 570, "₹15k-30k", False, False, False),
        ]

        for idx, (name_idx, profile, credit_score, income_range, is_fraudster, is_defaulter, is_blacklisted) in enumerate(user_profiles):
            name, email_prefix = INDIAN_NAMES[name_idx]
            email = f"{email_prefix}@example.com"
            email_hash = hash_for_lookup(email)

            # Skip if already exists
            if User.query.filter_by(email_hash=email_hash).first():
                continue

            # Random DOB (25-50 years old)
            age = random.randint(25, 50)
            dob = date.today() - relativedelta(years=age)
            account_created = random_date(365, 30)

            user = User(
                name_encrypted=encrypt_field(name),
                email_encrypted=encrypt_field(email),
                email_hash=email_hash,
                phone_encrypted=encrypt_field(f"+91 {random.randint(7000000000, 9999999999)}"),
                password_hash=bcrypt.generate_password_hash("Demo@1234").decode('utf-8'),
                monthly_income_range=income_range,
                city=random.choice(INDIAN_CITIES),
                date_of_birth=dob,
                account_created_at=account_created,
                kyc_status='verified',
                agreement_signed=True,
                agreement_signed_at=account_created + timedelta(hours=1),
                is_blacklisted=is_blacklisted,
                credit_score=credit_score,
                credit_limit=CREDIT_LIMITS[income_range],
                trust_score=max(10, min(100, credit_score // 9)),
                last_login=random_date(7, 0),
                is_active=not is_blacklisted,
            )
            db.session.add(user)
            db.session.flush()

            # KYC Record
            kyc = KYCRecord(
                user_id=user.id,
                pan_encrypted=encrypt_field(random.choice(PAN_PATTERNS)),
                aadhaar_last4=str(random.randint(1000, 9999)),
                liveness_score=round(random.uniform(0.82, 0.98), 4),
                deepfake_score=round(random.uniform(0.01, 0.08), 4),
                face_match_score=round(random.uniform(0.78, 0.97), 4),
                verification_status='verified',
                verified_at=account_created + timedelta(minutes=30),
                created_at=account_created,
            )
            db.session.add(kyc)

            # Generate transaction history (3-15 transactions per user)
            num_transactions = random.randint(3, 15)
            income_val = INCOME_VALUES[income_range]

            for t_idx in range(num_transactions):
                product = random.choice(PRODUCTS)
                t_date = random_date(300, 1)

                # Fraudsters have suspicious patterns
                if is_fraudster and t_idx % 3 == 0:
                    amount = random.uniform(30000, 80000)  # Unusually high
                    fraud_score = round(random.uniform(0.65, 0.95), 4)
                    is_flagged = True
                    fraud_reason = random.choice([
                        "High value transaction: amount exceeds 5x average",
                        "Unusual transaction hour: 2-4 AM activity detected",
                        "Velocity fraud: 8+ transactions in 24 hours",
                        "Location anomaly: transaction from different city",
                        "Device change detected with high-value transaction",
                    ])
                else:
                    amount = random.uniform(500, min(income_val * 0.3, 20000))
                    fraud_score = round(random.uniform(0.01, 0.18), 4)
                    is_flagged = False
                    fraud_reason = None

                transaction = Transaction(
                    user_id=user.id,
                    amount=round(amount, 2),
                    product_name=product[0],
                    category=product[1],
                    transaction_type='purchase',
                    transaction_at=t_date,
                    fraud_score=fraud_score,
                    is_flagged=is_flagged,
                    fraud_reason=fraud_reason,
                    status='approved' if not is_flagged else 'flagged',
                )
                db.session.add(transaction)
                db.session.flush()

                # Add fraud log for flagged transactions
                if is_flagged:
                    fraud_log = FraudLog(
                        user_id=user.id,
                        transaction_id=transaction.id,
                        fraud_type=fraud_reason.split(':')[0] if fraud_reason else "Anomaly",
                        fraud_score=fraud_score,
                        detection_model=random.choice(['IsolationForest', 'RandomForest', 'RuleEngine']),
                        flagged_at=t_date,
                        resolved=random.choice([True, False]),
                        admin_notes="Under review" if not is_blacklisted else "Confirmed fraud - user blacklisted",
                    )
                    db.session.add(fraud_log)

            # Create BNPL Plans for eligible users (credit_score >= 550)
            if credit_score >= 550 and not is_blacklisted:
                num_plans = random.randint(1, 3)
                for p_idx in range(num_plans):
                    tenure = random.choice([3, 6, 9])
                    plan_amount = round(random.uniform(2000, min(income_val * 2, 50000)), 2)
                    fee_rate = 0.0 if credit_score >= 750 else 0.02 if credit_score >= 650 else 0.04
                    processing_fee = round(plan_amount * fee_rate, 2)
                    total_payable = plan_amount + processing_fee
                    emi_amount = round(total_payable / tenure, 2)

                    plan_start = (account_created + timedelta(days=random.randint(1, 60))).date()
                    plan_end = plan_start + relativedelta(months=tenure)

                    # Determine plan status
                    if is_defaulter and p_idx == 0:
                        plan_status = 'defaulted'
                    elif plan_end < date.today():
                        plan_status = 'completed'
                    else:
                        plan_status = 'active'

                    plan = BNPLPlan(
                        user_id=user.id,
                        total_amount=plan_amount,
                        tenure_months=tenure,
                        emi_amount=emi_amount,
                        processing_fee=processing_fee,
                        start_date=plan_start,
                        end_date=plan_end,
                        status=plan_status,
                        created_at=datetime.combine(plan_start, datetime.min.time()),
                    )
                    db.session.add(plan)
                    db.session.flush()

                    # Create repayment schedule
                    for month_idx in range(1, tenure + 1):
                        due_date = plan_start + relativedelta(months=month_idx)
                        is_past_due = due_date < date.today()

                        if plan_status == 'completed':
                            status = 'paid'
                            paid_at = datetime.combine(due_date - timedelta(days=random.randint(0, 2)), datetime.min.time())
                            amount_paid = emi_amount
                            late_fee = 0
                        elif plan_status == 'defaulted':
                            if month_idx == 1:
                                status = 'paid'
                                paid_at = datetime.combine(due_date, datetime.min.time())
                                amount_paid = emi_amount
                                late_fee = 0
                            else:
                                status = 'overdue'
                                paid_at = None
                                amount_paid = 0
                                late_fee = round(emi_amount * 0.02, 2)
                        elif is_past_due and is_defaulter:
                            status = 'overdue'
                            paid_at = None
                            amount_paid = 0
                            late_fee = round(emi_amount * 0.02, 2)
                        elif is_past_due:
                            # Paid late or on time
                            days_late = random.randint(-2, 5)
                            status = 'paid'
                            paid_at = datetime.combine(due_date + timedelta(days=days_late), datetime.min.time())
                            amount_paid = emi_amount
                            late_fee = round(emi_amount * 0.01, 2) if days_late > 0 else 0
                        else:
                            status = 'pending'
                            paid_at = None
                            amount_paid = 0
                            late_fee = 0

                        repayment = Repayment(
                            plan_id=plan.id,
                            user_id=user.id,
                            due_date=due_date,
                            amount_due=emi_amount,
                            amount_paid=amount_paid,
                            paid_at=paid_at,
                            status=status,
                            late_fee=late_fee,
                        )
                        db.session.add(repayment)

            users_created.append((user.id, name, profile, credit_score))
            print(f"  Created: {name} | Profile: {profile.upper()} | Score: {credit_score} | Fraud: {is_fraudster} | Blacklisted: {is_blacklisted}")

        db.session.commit()
        print()
        print("=" * 60)
        print(f"SEEDING COMPLETE!")
        print(f"Users created: {len(users_created)}")
        print(f"All demo users password: Demo@1234")
        print()
        print("User categories:")
        print(f"  Excellent (750-900): 11 users")
        print(f"  Good (650-749): 11 users")
        print(f"  Fair (550-649): 10 users")
        print(f"  Poor/Fraudulent (<550): 10 users + 8 mixed")
        print()
        print("To login as any user:")
        print("  Email: arjun.sharma@example.com")
        print("  Password: Demo@1234")
        print()
        print("Check pgAdmin to see all data!")
        print("=" * 60)

if __name__ == '__main__':
    seed_database()
