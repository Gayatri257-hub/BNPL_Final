import random
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_required

from extensions import db
from models.bnpl_plan import BNPLPlan
from models.fraud_log import FraudLog
from models.repayment import Repayment
from models.transaction import Transaction
from routes.shop import PRODUCTS

# ML imports (fail-safe — models may not be trained yet)
try:
    from ml.credit_scorer import get_credit_score as _ml_credit
    from ml.fraud_detector import get_fraud_score as _ml_fraud
    from ml.emi_optimizer import get_optimal_emi_plan as _ml_emi
except ImportError:
    _ml_credit = _ml_fraud = _ml_emi = None


bnpl_bp = Blueprint('bnpl', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cart_total():
    """Compute cart total including 18 % GST."""
    cart_items = session.get('cart', [])
    subtotal = sum(
        next((p['price'] for p in PRODUCTS if p['id'] == item['id']), 0) * item['quantity']
        for item in cart_items
    )
    return round(subtotal * 1.18, 2)


def _get_interest_rate(credit_score: int, months: int) -> float:
    """Return annual interest rate (%) based on credit score and tenure."""
    if credit_score >= 750:
        base = 0.0   # interest-free for excellent credit
    elif credit_score >= 700:
        base = 1.5
    elif credit_score >= 650:
        base = 3.0
    else:
        base = 5.0
    # Longer tenure slight premium
    tenure_premium = {3: 0.0, 6: 0.5, 9: 1.0}.get(months, 1.5)
    return base + tenure_premium


def _calc_emi(principal: float, annual_rate: float, months: int) -> float:
    """Flat-rate EMI calculation (used for simplicity in BNPL context)."""
    if annual_rate == 0:
        return round(principal / months, 2)
    monthly_rate = annual_rate / 12 / 100
    emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
    return round(emi, 2)


def _processing_fee(principal: float, credit_score: int) -> float:
    if credit_score >= 750:
        return 0.0
    elif credit_score >= 700:
        return round(principal * 0.005, 2)
    return round(principal * 0.01, 2)


def _fallback_plans(total: float, credit_score: int) -> list:
    """Generate EMI plans without ML models (pure helper logic)."""
    plans = []
    for months in [3, 6, 9]:
        rate = _get_interest_rate(credit_score, months)
        emi  = _calc_emi(total, rate, months)
        fee  = _processing_fee(total, credit_score)
        plans.append({
            'months':         months,
            'tenure_months':  months,
            'emi':            emi,
            'emi_amount':     emi,
            'annual_rate':    rate,
            'processing_fee': fee,
            'total_payable':  round(emi * months + fee, 2),
            'recommended':    months == 6,
        })
    return plans


# ---------------------------------------------------------------------------
# Step 1 – Permissions
# ---------------------------------------------------------------------------

@bnpl_bp.route('/permissions')
@login_required
def permissions():
    cart_items = session.get('cart', [])
    if not cart_items:
        return redirect(url_for('shop.cart'))
    return render_template('bnpl/permissions.html')


# ---------------------------------------------------------------------------
# Step 2 – Credit & Fraud Check
# ---------------------------------------------------------------------------

@bnpl_bp.route('/credit-check', methods=['GET', 'POST'])
@login_required
def credit_check():
    if request.method == 'POST':
        session['bnpl_location'] = request.form.get('location', 'Unknown')
        session['bnpl_device'] = request.form.get('device_info', 'Unknown')

    # Try loading trained ML models; fall back to randomised scores
    try:
        from ml.credit_scorer import get_credit_score
        from ml.fraud_detector import get_fraud_score
        score_result = get_credit_score(current_user)
        fraud_result = get_fraud_score(current_user, session.get('cart', []))
    except Exception:
        score_result = {
            'credit_score': random.randint(600, 850),
            'approval_probability': round(random.uniform(0.70, 0.95), 4),
            'risk_category': 'LOW',
            'sub_scores': {
                'payment_history': random.randint(70, 95),
                'fraud_risk':      random.randint(5, 20),
                'behavioral':      random.randint(65, 90),
                'velocity':        random.randint(60, 88),
                'identity':        random.randint(80, 98),
            },
        }
        fraud_result = {
            'is_fraud': False,
            'fraud_score': round(random.uniform(0.01, 0.15), 4),
            'anomaly_type': 'None detected',
        }

    total_with_gst = _cart_total()
    approved = score_result['credit_score'] >= 550 and not fraud_result['is_fraud']

    session['credit_score_result'] = score_result
    session['fraud_result'] = fraud_result
    session['bnpl_total'] = total_with_gst
    session['bnpl_approved'] = approved

    return render_template(
        'bnpl/credit_score.html',
        score_result=score_result,
        fraud_result=fraud_result,
        approved=approved,
        total_amount=total_with_gst,
    )


# ---------------------------------------------------------------------------
# Step 3 – Payment Plan Selection
# ---------------------------------------------------------------------------

@bnpl_bp.route('/payment-plan')
@login_required
def payment_plan():
    if not session.get('bnpl_approved'):
        return redirect(url_for('bnpl.credit_check'))

    total        = float(session.get('bnpl_total', 0))
    credit_score = session.get('credit_score_result', {}).get('credit_score', 650)

    # ── Use ML EMI optimizer ──────────────────────────────────────────────────
    if _ml_emi:
        try:
            emi_result = _ml_emi(current_user, total)
            plans = emi_result['plans']
        except Exception:
            plans = _fallback_plans(total, credit_score)
    else:
        plans = _fallback_plans(total, credit_score)

    # Persist selected plan options to session for the confirm step
    session['bnpl_plans'] = plans
    session.modified = True

    return render_template(
        'bnpl/payment_plan.html',
        plans=plans,
        total_amount=total,
        credit_score=credit_score,
    )


# ---------------------------------------------------------------------------
# Step 4 – Confirm & Activate BNPL Plan
# ---------------------------------------------------------------------------

@bnpl_bp.route('/confirm', methods=['POST'])
@login_required
def confirm():
    if not session.get('bnpl_approved'):
        return redirect(url_for('bnpl.credit_check'))

    months       = int(request.form.get('months', 6))
    total        = float(session.get('bnpl_total', 0))
    credit_score = session.get('credit_score_result', {}).get('credit_score', 650)

    # Look up the selected plan from session (set by payment_plan route)
    selected_plan = next(
        (p for p in session.get('bnpl_plans', []) if p.get('months') == months),
        None
    )
    if selected_plan:
        emi = float(selected_plan.get('emi_amount') or selected_plan.get('emi', 0))
        fee = float(selected_plan.get('processing_fee', 0))
    else:
        # Fallback: recalculate
        rate = _get_interest_rate(credit_score, months)
        emi  = _calc_emi(total, rate, months)
        fee  = _processing_fee(total, credit_score)

    today = date.today()
    end_date = today + relativedelta(months=months)

    plan = BNPLPlan(
        user_id=current_user.id,
        total_amount=total,
        tenure_months=months,
        emi_amount=emi,
        processing_fee=fee,
        start_date=today,
        end_date=end_date,
        status='active',
    )
    db.session.add(plan)
    db.session.flush()  # get plan.id before repayments

    # Create repayment schedule
    for i in range(1, months + 1):
        due = today + relativedelta(months=i)
        repayment = Repayment(
            plan_id=plan.id,
            user_id=current_user.id,
            due_date=due,
            amount_due=emi,
        )
        db.session.add(repayment)

    # Log as a transaction
    cart_items = session.get('cart', [])
    product_names = ', '.join(
        next((p['name'] for p in PRODUCTS if p['id'] == item['id']), 'Unknown')
        for item in cart_items
    )
    txn = Transaction(
        user_id=current_user.id,
        amount=total,
        product_name=product_names[:255],
        category='BNPL Purchase',
        transaction_type='purchase',
        status='approved',
        fraud_score=session.get('fraud_result', {}).get('fraud_score', 0.0),
        is_flagged=False,
    )
    db.session.add(txn)

    db.session.commit()

    # Clear cart and session state
    session.pop('cart', None)
    session.pop('bnpl_approved', None)
    session.pop('credit_score_result', None)
    session.pop('fraud_result', None)
    session.pop('bnpl_total', None)
    session.modified = True

    return redirect(url_for('bnpl.success', plan_id=plan.id))


# ---------------------------------------------------------------------------
# Step 5 – Success
# ---------------------------------------------------------------------------

@bnpl_bp.route('/success/<int:plan_id>')
@login_required
def success(plan_id):
    plan = BNPLPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    repayments = Repayment.query.filter_by(plan_id=plan.id).order_by(Repayment.due_date).all()
    return render_template('bnpl/success.html', plan=plan, repayments=repayments)


# ---------------------------------------------------------------------------
# Repayment History & Pay EMI
# ---------------------------------------------------------------------------

@bnpl_bp.route('/repayments')
@bnpl_bp.route('/my-plans')
@login_required
def repayments():
    plans = BNPLPlan.query.filter_by(user_id=current_user.id).order_by(BNPLPlan.created_at.desc()).all()
    all_repayments = (
        Repayment.query.filter_by(user_id=current_user.id)
        .order_by(Repayment.due_date.asc())
        .all()
    )
    return render_template('bnpl/repayments.html', plans=plans, repayments=all_repayments)


@bnpl_bp.route('/pay-emi/<int:repayment_id>', methods=['POST'])
@login_required
def pay_emi(repayment_id):
    repayment = Repayment.query.filter_by(id=repayment_id, user_id=current_user.id).first_or_404()

    if repayment.status == 'paid':
        return jsonify({'success': False, 'message': 'Already paid.'})

    total_due = float(repayment.amount_due) + float(repayment.late_fee)
    repayment.amount_paid = total_due
    repayment.paid_at = datetime.utcnow()
    repayment.status = 'paid'

    # Log the EMI payment as a transaction
    txn = Transaction(
        user_id=current_user.id,
        amount=total_due,
        product_name=f'EMI Payment – Plan #{repayment.plan_id}',
        category='EMI',
        transaction_type='emi_payment',
        status='approved',
    )
    db.session.add(txn)

    # Check if entire plan is now complete
    plan = BNPLPlan.query.get(repayment.plan_id)
    if plan:
        remaining = Repayment.query.filter(
            Repayment.plan_id == plan.id,
            Repayment.status != 'paid',
            Repayment.id != repayment_id,
        ).count()
        if remaining == 0:
            plan.status = 'completed'

    db.session.commit()
    return jsonify({'success': True, 'message': 'EMI paid successfully.'})
