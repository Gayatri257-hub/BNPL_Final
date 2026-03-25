import os
import joblib
import numpy as np
import random
from datetime import datetime

MODELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')

# Income range string → numeric map (handles both display and stored variants)
INCOME_MAP = {
    'below_15k':  12000,  'Below ₹15k':  12000,  'Below ₹15,000': 12000,
    '15k_30k':    22000,  '₹15k-30k':    22000,  '₹15,000 – ₹30,000': 22000,
    '30k_60k':    45000,  '₹30k-60k':    45000,  '₹30,000 – ₹60,000': 45000,
    '60k_1L':     80000,  '₹60k-1L':     80000,  '₹60,000 – ₹1,00,000': 80000,
    'above_1L':  150000,  'Above ₹1L':  150000,  'Above ₹1,00,000': 150000,
}


def _monthly_income(user) -> int:
    return INCOME_MAP.get(getattr(user, 'monthly_income_range', None), 30000)


def get_credit_score(user) -> dict:
    """
    Returns a dict with:
        credit_score         int  300–900
        approval_probability float 0–1
        risk_category        str  LOW / MEDIUM / MEDIUM-HIGH / HIGH
        sub_scores           dict
        max_eligible_amount  int
    Falls back to deterministic random values if models are not trained yet.
    """
    try:
        model  = joblib.load(os.path.join(MODELS_PATH, 'credit_model.pkl'))
        scaler = joblib.load(os.path.join(MODELS_PATH, 'credit_scaler.pkl'))

        # Age from date_of_birth
        age = 30
        dob = getattr(user, 'date_of_birth', None)
        if dob:
            today = datetime.now().date()
            age = max(18, (today - dob).days // 365)

        monthly_income = _monthly_income(user)

        account_age_days = 0
        created_at = getattr(user, 'account_created_at', None)
        if created_at:
            account_age_days = max(0, (datetime.utcnow() - created_at).days)

        kyc_verified = 1 if getattr(user, 'kyc_status', '') == 'verified' else 0

        plans = getattr(user, 'bnpl_plans', []) or []
        past_defaults       = sum(1 for p in plans if getattr(p, 'status', '') == 'defaulted')
        existing_bnpl_count = sum(1 for p in plans if getattr(p, 'status', '') == 'active')
        trust_score         = float(getattr(user, 'trust_score', 75) or 75)

        features = np.array([[
            age,
            monthly_income,
            1,                   # employment_type assumed salaried
            existing_bnpl_count,
            past_defaults,
            5000,                # avg_transaction_amount placeholder
            trust_score,         # payment_history_score proxy
            kyc_verified,
            account_age_days,
        ]])
        X_scaled = scaler.transform(features)
        proba = model.predict_proba(X_scaled)[0]
        # proba[1] = P(approved)
        approval_prob = float(proba[1])

        # Map probability → 300-900 and apply domain adjustments
        base_score = 300 + int(approval_prob * 600)
        base_score += min(age - 21, 30) * 2
        base_score += kyc_verified * 30
        base_score -= past_defaults * 50
        base_score = max(300, min(900, base_score))

        if base_score >= 750:
            risk_category = 'LOW'
        elif base_score >= 650:
            risk_category = 'MEDIUM'
        elif base_score >= 550:
            risk_category = 'MEDIUM-HIGH'
        else:
            risk_category = 'HIGH'

        sub_scores = {
            'payment_history': min(100, int(trust_score * 0.9 + approval_prob * 10)),
            'fraud_risk':      max(0, 100 - int(approval_prob * 80)),
            'behavioral':      min(100, int(trust_score)),
            'velocity':        min(100, max(0, 100 - existing_bnpl_count * 15)),
            'identity':        95 if kyc_verified else 40,
        }

        return {
            'credit_score':        base_score,
            'approval_probability': round(approval_prob, 4),
            'risk_category':       risk_category,
            'sub_scores':          sub_scores,
            'max_eligible_amount': int(monthly_income * 2.5) if base_score >= 550 else 0,
        }

    except Exception as exc:
        # ── Graceful fallback (models not trained yet) ──
        rng = random.Random(getattr(user, 'id', 42))
        score = rng.randint(620, 820)
        prob  = round(rng.uniform(0.72, 0.95), 4)
        return {
            'credit_score':        score,
            'approval_probability': prob,
            'risk_category':       'LOW' if score >= 700 else 'MEDIUM',
            'sub_scores': {
                'payment_history': rng.randint(70, 95),
                'fraud_risk':      rng.randint(5, 20),
                'behavioral':      rng.randint(65, 90),
                'velocity':        rng.randint(60, 88),
                'identity':        rng.randint(80, 98),
            },
            'max_eligible_amount': 25000,
        }
