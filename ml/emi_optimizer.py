import os
import joblib
import numpy as np

MODELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')

INCOME_MAP = {
    'below_15k':  12000,  'Below ₹15k':  12000,  'Below ₹15,000': 12000,
    '15k_30k':    22000,  '₹15k-30k':    22000,  '₹15,000 – ₹30,000': 22000,
    '30k_60k':    45000,  '₹30k-60k':    45000,  '₹30,000 – ₹60,000': 45000,
    '60k_1L':     80000,  '₹60k-1L':     80000,  '₹60,000 – ₹1,00,000': 80000,
    'above_1L':  150000,  'Above ₹1L':  150000,  'Above ₹1,00,000': 150000,
}

# Interest / processing fee tiers keyed by credit score thresholds
FEE_TIERS = [
    (750, 0.000, 0.00),   # score >= 750 → 0% annual rate, 0% processing
    (700, 0.015, 0.01),   # score >= 700 → 1.5% annual, 1% processing
    (650, 0.030, 0.02),   # score >= 650 → 3% annual,   2% processing
    (550, 0.050, 0.03),   # score >= 550 → 5% annual,   3% processing
    (  0, 0.080, 0.04),   # below 550    → 8% annual,   4% processing
]


def _get_fee_rates(credit_score: int, months: int) -> tuple:
    """Return (annual_rate, processing_fee_rate) for a given score and tenure."""
    annual_rate, proc_rate = 0.08, 0.04
    for threshold, ar, pr in FEE_TIERS:
        if credit_score >= threshold:
            annual_rate, proc_rate = ar, pr
            break
    # Add small surcharge for longer tenures
    if months == 9:
        annual_rate += 0.01
    return annual_rate, proc_rate


def get_optimal_emi_plan(user, total_amount: float) -> dict:
    """
    Returns:
        plans               list of plan dicts
        recommended_tenure  int (3 / 6 / 9)
        max_eligible_amount int
    """
    credit_score   = int(getattr(user, 'credit_score', None) or 650)
    monthly_income = INCOME_MAP.get(getattr(user, 'monthly_income_range', None), 30000)
    plans_list     = getattr(user, 'bnpl_plans', []) or []
    past_defaults  = sum(1 for p in plans_list if getattr(p, 'status', '') == 'defaulted')
    existing_loans = sum(1 for p in plans_list if getattr(p, 'status', '') == 'active')

    # ── Try ML-based tenure recommendation ─────────────────────────────────────
    recommended_tenure = 6  # sensible default
    try:
        knn    = joblib.load(os.path.join(MODELS_PATH, 'emi_knn_model.pkl'))
        dt     = joblib.load(os.path.join(MODELS_PATH, 'emi_dt_model.pkl'))
        scaler = joblib.load(os.path.join(MODELS_PATH, 'emi_scaler.pkl'))

        features = np.array([[credit_score, monthly_income, past_defaults, existing_loans]])
        X_scaled = scaler.transform(features)

        knn_tenure = int(knn.predict(X_scaled)[0])
        dt_tenure  = int(dt.predict(X_scaled)[0])
        avg_tenure = (knn_tenure + dt_tenure) / 2

        # Snap to allowed values
        recommended_tenure = min([3, 6, 9], key=lambda x: abs(x - avg_tenure))

    except Exception:
        # Deterministic fallback
        if credit_score >= 750 and past_defaults == 0:
            recommended_tenure = 9
        elif credit_score >= 650:
            recommended_tenure = 6
        else:
            recommended_tenure = 3

    # ── Build plan options ──────────────────────────────────────────────────────
    plans = []
    for months in [3, 6, 9]:
        annual_rate, proc_rate = _get_fee_rates(credit_score, months)

        # Monthly interest (flat rate simplified)
        monthly_rate    = annual_rate / 12
        interest_total  = total_amount * monthly_rate * months
        processing_fee  = round(total_amount * proc_rate, 2)
        total_payable   = round(total_amount + interest_total + processing_fee, 2)
        emi             = round(total_payable / months, 2)

        plans.append({
            'months':          months,            # used by template loop
            'tenure_months':   months,            # used by bnpl route
            'emi':             emi,               # template uses plan.emi
            'emi_amount':      emi,               # route stores this
            'processing_fee':  processing_fee,
            'annual_rate':     round(annual_rate * 100, 1),
            'total_payable':   total_payable,
            'recommended':     months == recommended_tenure,
        })

    return {
        'plans':               plans,
        'recommended_tenure':  recommended_tenure,
        'max_eligible_amount': int(monthly_income * 2.5),
    }
