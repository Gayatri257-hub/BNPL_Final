"""
SmartPay DB migration — adds credit_limit column to users table
and populates it from monthly_income_range.
Run once: python migrate_credit_limit.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import application

INCOME_CREDIT_MAP = {
    'below_15000':   14999,
    '15000_30000':   25000,
    '30000_50000':   45000,
    '50000_100000':  80000,
    'above_100000': 150000,
}

with application.app_context():
    from extensions import db
    from sqlalchemy import text

    # 1. Add column if it doesn't exist yet
    try:
        with db.engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(10,2) DEFAULT 10000;"
            ))
            conn.commit()
        print("✅ Column credit_limit ensured (added or already existed).")
    except Exception as e:
        print(f"⚠️  ALTER TABLE error: {e}")

    # 2. Add fraud_reason column to transactions if missing
    try:
        with db.engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS fraud_reason VARCHAR(500);"
            ))
            conn.commit()
        print("✅ Column fraud_reason ensured in transactions.")
    except Exception as e:
        print(f"⚠️  fraud_reason: {e}")

    # 3. Populate credit_limit from income range for existing users
    from models.user import User
    users = User.query.all()
    updated = 0
    for u in users:
        if u.credit_limit is None or float(u.credit_limit) == 0:
            u.credit_limit = INCOME_CREDIT_MAP.get(u.monthly_income_range, 10000)
            updated += 1
    db.session.commit()
    print(f"✅ Set credit_limit for {updated} existing user(s) from income range.")

    print("\n📊 Current users:")
    for u in users:
        print(f"   User #{u.id}: income={u.monthly_income_range!r} → limit=₹{u.credit_limit}")

    # 4. Show table counts
    from models.transaction import Transaction
    from models.fraud_log import FraudLog
    from models.bnpl_plan import BNPLPlan
    from models.repayment import Repayment
    print(f"\n📦 Table row counts:")
    print(f"   users:        {User.query.count()}")
    print(f"   transactions: {Transaction.query.count()}")
    print(f"   fraud_logs:   {FraudLog.query.count()}")
    print(f"   bnpl_plans:   {BNPLPlan.query.count()}")
    print(f"   repayments:   {Repayment.query.count()}")
