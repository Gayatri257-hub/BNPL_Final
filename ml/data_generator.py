import pandas as pd
import numpy as np
import random

try:
    from faker import Faker
    fake = Faker('en_IN')
except ImportError:
    fake = None


def generate_credit_dataset(n=10000):
    np.random.seed(42)
    random.seed(42)
    data = []
    for _ in range(n):
        age = random.randint(21, 58)
        monthly_income = random.choice([
            random.randint(10000, 15000),
            random.randint(15000, 30000),
            random.randint(30000, 60000),
            random.randint(60000, 100000),
            random.randint(100000, 200000)
        ])
        employment_type = random.choice([0, 1, 2])  # 0=unemployed, 1=salaried, 2=self-employed
        existing_bnpl_count = random.randint(0, 5)
        past_defaults = random.randint(0, 3)
        avg_transaction_amount = random.uniform(500, 25000)
        payment_history_score = random.uniform(0, 100)
        kyc_verified = random.choice([0, 1])
        account_age_days = random.randint(0, 1825)

        # Deterministic credit score logic
        score = 300
        score += min(age - 21, 30) * 3
        score += min(monthly_income / 1000, 150)
        score += employment_type * 50
        score -= past_defaults * 80
        score += payment_history_score * 2
        score += kyc_verified * 50
        score += min(account_age_days / 10, 100)
        score -= existing_bnpl_count * 20
        score += np.random.normal(0, 30)
        score = max(300, min(900, score))

        approved = 1 if score >= 550 else 0

        data.append({
            'age': age,
            'monthly_income': monthly_income,
            'employment_type': employment_type,
            'existing_bnpl_count': existing_bnpl_count,
            'past_defaults': past_defaults,
            'avg_transaction_amount': avg_transaction_amount,
            'payment_history_score': payment_history_score,
            'kyc_verified': kyc_verified,
            'account_age_days': account_age_days,
            'credit_score': int(score),
            'approved': approved
        })
    return pd.DataFrame(data)


def generate_fraud_dataset(n=10000):
    np.random.seed(42)
    random.seed(42)
    data = []
    for _ in range(n):
        transaction_amount = random.uniform(100, 50000)
        transaction_hour = random.randint(0, 23)
        transactions_last_24h = random.randint(0, 20)
        amount_vs_avg_ratio = random.uniform(0.1, 10.0)
        location_change_flag = random.choice([0, 1])
        device_change_flag = random.choice([0, 1])
        velocity_score = random.uniform(0, 100)
        ip_risk_score = random.uniform(0, 1)

        fraud_probability = 0.02
        if transaction_amount > 30000:
            fraud_probability += 0.15
        if transactions_last_24h > 10:
            fraud_probability += 0.20
        if amount_vs_avg_ratio > 5:
            fraud_probability += 0.25
        if location_change_flag and device_change_flag:
            fraud_probability += 0.30
        if transaction_hour in [1, 2, 3, 4]:
            fraud_probability += 0.10
        if ip_risk_score > 0.7:
            fraud_probability += 0.15

        is_fraud = 1 if random.random() < min(fraud_probability, 0.95) else 0

        data.append({
            'transaction_amount': transaction_amount,
            'transaction_hour': transaction_hour,
            'transactions_last_24h': transactions_last_24h,
            'amount_vs_avg_ratio': amount_vs_avg_ratio,
            'location_change_flag': location_change_flag,
            'device_change_flag': device_change_flag,
            'velocity_score': velocity_score,
            'ip_risk_score': ip_risk_score,
            'is_fraud': is_fraud
        })
    return pd.DataFrame(data)


def generate_late_payment_dataset(n=10000):
    np.random.seed(42)
    random.seed(42)
    data = []
    for _ in range(n):
        days_since_last_payment = random.randint(0, 60)
        missed_payments_count = random.randint(0, 5)
        income_to_emi_ratio = random.uniform(0.5, 10.0)
        spending_volatility = random.uniform(0, 1)
        salary_day_proximity = random.randint(0, 30)
        active_loans_count = random.randint(0, 5)

        late_prob = 0.05
        if missed_payments_count > 2:
            late_prob += 0.35
        if income_to_emi_ratio < 2:
            late_prob += 0.25
        if days_since_last_payment > 30:
            late_prob += 0.20
        if spending_volatility > 0.7:
            late_prob += 0.15
        if active_loans_count > 3:
            late_prob += 0.10

        will_pay_late = 1 if random.random() < min(late_prob, 0.95) else 0

        data.append({
            'days_since_last_payment': days_since_last_payment,
            'missed_payments_count': missed_payments_count,
            'income_to_emi_ratio': income_to_emi_ratio,
            'spending_volatility': spending_volatility,
            'salary_day_proximity': salary_day_proximity,
            'active_loans_count': active_loans_count,
            'will_pay_late': will_pay_late
        })
    return pd.DataFrame(data)
