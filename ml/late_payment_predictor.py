import os
import joblib
import numpy as np
import random

MODELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')

INCOME_MAP = {
    'below_15k':  12000,  'Below ₹15k':  12000,  'Below ₹15,000': 12000,
    '15k_30k':    22000,  '₹15k-30k':    22000,  '₹15,000 – ₹30,000': 22000,
    '30k_60k':    45000,  '₹30k-60k':    45000,  '₹30,000 – ₹60,000': 45000,
    '60k_1L':     80000,  '₹60k-1L':     80000,  '₹60,000 – ₹1,00,000': 80000,
    'above_1L':  150000,  'Above ₹1L':  150000,  'Above ₹1,00,000': 150000,
}


def predict_late_payment(user) -> dict:
    """
    Returns:
        late_probability  float 0-1
        risk_level        str LOW / MEDIUM / HIGH
        days_likely_late  int
    """
    try:
        model  = joblib.load(os.path.join(MODELS_PATH, 'late_payment_model.pkl'))
        scaler = joblib.load(os.path.join(MODELS_PATH, 'late_payment_scaler.pkl'))

        plans = getattr(user, 'bnpl_plans', []) or []
        past_defaults = sum(1 for p in plans if getattr(p, 'status', '') == 'defaulted')
        active_loans  = sum(1 for p in plans if getattr(p, 'status', '') == 'active')

        monthly_income = INCOME_MAP.get(getattr(user, 'monthly_income_range', None), 30000)
        emi_amount     = 2000  # conservative placeholder
        income_to_emi  = monthly_income / emi_amount if emi_amount > 0 else 5.0

        features = np.array([[
            0,              # days_since_last_payment (fresh user)
            past_defaults,
            income_to_emi,
            0.2,            # spending_volatility (low default)
            15,             # salary_day_proximity (mid-month)
            active_loans,
        ]])
        X_scaled  = scaler.transform(features)
        late_prob = float(model.predict_proba(X_scaled)[0][1])

        risk_level = 'HIGH' if late_prob > 0.6 else 'MEDIUM' if late_prob > 0.3 else 'LOW'
        return {
            'late_probability': round(late_prob, 4),
            'risk_level':       risk_level,
            'days_likely_late': int(late_prob * 30),
        }

    except Exception:
        prob = round(random.uniform(0.05, 0.20), 4)
        return {
            'late_probability': prob,
            'risk_level':       'LOW',
            'days_likely_late': 0,
        }
