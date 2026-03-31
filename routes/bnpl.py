import random
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session, url_for, flash)
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

# Income → credit limit mapping (same as in auth.py)
INCOME_CREDIT_MAP = {
    'below_15000':   14999,
    '15000_30000':   25000,
    '30000_50000':   45000,
    '50000_100000':  80000,
    'above_100000': 150000,
}


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
        base = 0.0
    elif credit_score >= 700:
        base = 1.5
    elif credit_score >= 650:
        base = 3.0
    else:
        base = 5.0
    tenure_premium = {3: 0.0, 6: 0.5, 9: 1.0}.get(months, 1.5)
    return base + tenure_premium


def _calc_emi(principal: float, annual_rate: float, months: int) -> float:
    """Flat-rate EMI calculation."""
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
    """Generate EMI plans without ML models."""
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


def _save_transaction(user_id, amount, product_name, category, txn_type, status,
                      fraud_score=0.0, is_flagged=False, fraud_reason=None):
    """Always persist a transaction record to the DB."""
    txn = Transaction(
        user_id=user_id,
        amount=amount,
        product_name=str(product_name)[:255],
        category=category,
        transaction_type=txn_type,
        status=status,
        fraud_score=fraud_score,
        is_flagged=is_flagged,
        fraud_reason=str(fraud_reason)[:500] if fraud_reason else None,
    )
    db.session.add(txn)
    db.session.flush()   # get txn.id without final commit
    return txn


def _save_fraud_log(user_id, transaction_id, fraud_type, fraud_score, model='RuleEngine+RF'):
    """Persist a FraudLog entry."""
    log = FraudLog(
        user_id=user_id,
        transaction_id=transaction_id,
        fraud_type=fraud_type,
        fraud_score=fraud_score,
        detection_model=model,
    )
    db.session.add(log)


def _run_fraud_checks(user, total_amount, cart_items):
    """
    Run all real-time fraud checks.
    Returns dict:
        blocked     bool  – hard deny
        flagged     bool  – soft flag (allow but mark)
        reason      str
        fraud_score float
        anomalies   list[str]
        risk_level  str
        score_result dict
        fraud_result dict
    """
    anomalies = []
    blocked   = False
    reason    = ''

    # ── 1. Credit Limit Check ────────────────────────────────────────────────
    user_limit     = float(user.credit_limit or INCOME_CREDIT_MAP.get(user.monthly_income_range, 10000))
    available_cred = float(user.available_credit)

    if total_amount > available_cred:
        blocked = True
        if total_amount > user_limit:
            reason = f'Transaction amount (₹{total_amount:,.2f}) exceeds your credit limit of ₹{user_limit:,.2f}'
            anomalies.append(f'Exceeds credit limit (₹{user_limit:,.2f})')
        else:
            reason = (f'Transaction amount (₹{total_amount:,.2f}) exceeds your available credit '
                      f'(₹{available_cred:,.2f}). Complete existing EMIs first.')
            anomalies.append(f'Exceeds available credit (₹{available_cred:,.2f})')

    # ── 2. ML Credit Score ───────────────────────────────────────────────────
    try:
        from ml.credit_scorer import get_credit_score
        score_result = get_credit_score(user)
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

    # ── 3. ML Fraud Score ────────────────────────────────────────────────────
    try:
        from ml.fraud_detector import get_fraud_score
        fraud_result = get_fraud_score(user, cart_items, total_amount)
    except Exception:
        # Derive a score from anomalies found
        base_score = 0.05
        if total_amount > 30000:
            base_score += 0.25
        if datetime.now().hour in [1, 2, 3, 4]:
            base_score += 0.20
        fraud_result = {
            'is_fraud':    base_score > 0.5,
            'fraud_score': round(min(base_score, 0.99), 4),
            'anomaly_type': ', '.join(anomalies) if anomalies else 'None detected',
            'risk_level':  'HIGH' if base_score > 0.7 else ('MEDIUM' if base_score > 0.3 else 'LOW'),
        }

    # ── 4. Rule-based anomaly detection ─────────────────────────────────────
    transaction_hour = datetime.now().hour
    txns = getattr(user, 'transactions', []) or []
    avg_amount = 5000.0
    if txns:
        recent_amounts = [float(t.amount) for t in txns[-10:] if hasattr(t, 'amount')]
        if recent_amounts:
            avg_amount = sum(recent_amounts) / len(recent_amounts)

    if total_amount > 30000:
        anomalies.append('High value transaction (>₹30,000)')
    if transaction_hour in [1, 2, 3, 4]:
        anomalies.append(f'Unusual hour ({transaction_hour}:00 AM)')
    if avg_amount > 0 and total_amount / avg_amount > 5:
        anomalies.append(f'Amount {total_amount/avg_amount:.1f}× above your average')
    if len(txns) > 10:
        anomalies.append('High transaction velocity')

    # Merge anomalies into fraud_result
    if anomalies and not blocked:
        fraud_result['anomaly_type'] = ', '.join(set(
            (fraud_result.get('anomaly_type') or '').split(', ') + anomalies
        )).strip(', ')

    # ── 5. Hard deny on ML is_fraud ─────────────────────────────────────────
    if not blocked and fraud_result.get('is_fraud'):
        blocked = True
        reason  = f"Fraud detected by AI model: {fraud_result.get('anomaly_type', 'suspicious pattern')}"

    # ── 6. Soft flag on low credit score ─────────────────────────────────────
    flagged = (fraud_result.get('risk_level') == 'HIGH' or
               score_result.get('credit_score', 700) < 550)

    risk_level = fraud_result.get('risk_level', 'LOW')

    return {
        'blocked':      blocked,
        'flagged':      flagged,
        'reason':       reason,
        'fraud_score':  fraud_result.get('fraud_score', 0.0),
        'anomalies':    anomalies,
        'risk_level':   risk_level,
        'score_result': score_result,
        'fraud_result': fraud_result,
        'user_limit':   user_limit,
        'available_credit': available_cred,
    }


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
        location = request.form.get('location', 'Unknown')
        device_info = request.form.get('device_info', 'Unknown')
        session['bnpl_location'] = location
        session['bnpl_device'] = device_info

    # ── Pull real DB records ──────────────────────────────────────────────────
    fraud_count = FraudLog.query.filter_by(user_id=current_user.id).count()
    flagged_transactions = Transaction.query.filter_by(
        user_id=current_user.id, is_flagged=True
    ).count()
    overdue_repayments = Repayment.query.filter_by(
        user_id=current_user.id, status='overdue'
    ).count()

    cart_items = session.get('cart', [])
    total = sum(
        next((p['price'] for p in PRODUCTS if p['id'] == item['id']), 0) * item['quantity']
        for item in cart_items
    )
    total_with_gst = round(total * 1.18, 2)

    # ── 1. Hard reject: blacklisted users ────────────────────────────────────
    if current_user.is_blacklisted:
        score_result = {
            'credit_score': 320,
            'approval_probability': 0.01,
            'risk_category': 'HIGH',
            'sub_scores': {'payment_history': 3, 'fraud_risk': 98, 'behavioral': 5, 'velocity': 8, 'identity': 20},
        }
        fraud_result = {
            'is_fraud': True,
            'fraud_score': 0.97,
            'anomaly_type': (
                f'BLACKLISTED ACCOUNT: {flagged_transactions} fraudulent transactions confirmed. '
                f'{fraud_count} fraud alerts on record. Account permanently flagged.'
            ),
            'risk_level': 'HIGH',
        }
        session['credit_score_result'] = score_result
        session['fraud_result'] = fraud_result
        session['bnpl_total'] = total_with_gst
        session['bnpl_approved'] = False
        return render_template('bnpl/credit_score.html',
            score_result=score_result, fraud_result=fraud_result,
            approved=False, total_amount=total_with_gst)

    # ── 2. Hard reject: significant fraud history ─────────────────────────────
    if fraud_count >= 3 or flagged_transactions >= 3:
        score_result = {
            'credit_score': max(300, (current_user.credit_score or 400) - 150),
            'approval_probability': 0.03,
            'risk_category': 'HIGH',
            'sub_scores': {'payment_history': 10, 'fraud_risk': 92, 'behavioral': 15, 'velocity': 12, 'identity': 35},
        }
        fraud_result = {
            'is_fraud': True,
            'fraud_score': round(min(0.97, 0.5 + fraud_count * 0.08 + flagged_transactions * 0.05), 4),
            'anomaly_type': (
                f'HIGH RISK: {flagged_transactions} flagged transactions detected. '
                f'{fraud_count} fraud alerts in system. Transaction blocked.'
            ),
            'risk_level': 'HIGH',
        }
        session['credit_score_result'] = score_result
        session['fraud_result'] = fraud_result
        session['bnpl_total'] = total_with_gst
        session['bnpl_approved'] = False
        return render_template('bnpl/credit_score.html',
            score_result=score_result, fraud_result=fraud_result,
            approved=False, total_amount=total_with_gst)

    # ── 3. Normal ML scoring for clean users ──────────────────────────────────
    try:
        from ml.credit_scorer import get_credit_score
        from ml.fraud_detector import get_fraud_score
        score_result = get_credit_score(current_user)
        fraud_result = get_fraud_score(current_user, cart_items)
    except Exception:
        score_result = {
            'credit_score': current_user.credit_score or random.randint(500, 750),
            'approval_probability': 0.7,
            'risk_category': 'LOW',
            'sub_scores': {
                'payment_history': 75,
                'fraud_risk': 15,
                'behavioral': 70,
                'velocity': 65,
                'identity': 85,
            },
        }
        fraud_result = {
            'is_fraud': False,
            'fraud_score': 0.05,
            'anomaly_type': 'None detected',
            'risk_level': 'LOW',
        }

    # ── 4. Apply overdue penalty ──────────────────────────────────────────────
    if overdue_repayments > 0:
        score_result['credit_score'] = max(300, score_result['credit_score'] - overdue_repayments * 40)

    # ── 5. Anchor to stored credit score ──────────────────────────────────────
    if current_user.credit_score and current_user.credit_score > 0:
        score_result['credit_score'] = min(score_result['credit_score'], current_user.credit_score + 50)
        score_result['credit_score'] = max(300, min(900, score_result['credit_score']))

    # ── 6. Final strict approval gate ─────────────────────────────────────────
    approved = (
    score_result['credit_score'] >= 550
    and not current_user.is_blacklisted
    and fraud_count < 3
    and flagged_count < 3
    and overdue_count == 0
    and fraud_result.get('fraud_score', 0) < 0.30
    )

    # Persist updated credit score
    try:
        current_user.credit_score = score_result['credit_score']
        db.session.commit()
    except Exception:
        db.session.rollback()

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
# Fraud Blocked Page
# ---------------------------------------------------------------------------

@bnpl_bp.route('/fraud-blocked')
@login_required
def fraud_blocked():
    block_data = session.get('fraud_block')
    if not block_data:
        return redirect(url_for('shop.cart'))
    return render_template(
        'bnpl/fraud_blocked.html',
        block_data=block_data,
        user_credit_limit=float(current_user.credit_limit or 0),
        available_credit=float(current_user.available_credit),
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

    if _ml_emi:
        try:
            emi_result = _ml_emi(current_user, total)
            plans = emi_result['plans']
        except Exception:
            plans = _fallback_plans(total, credit_score)
    else:
        plans = _fallback_plans(total, credit_score)

    session['bnpl_plans'] = plans
    session.modified = True

    return render_template(
        'bnpl/payment_plan.html',
        plans=plans,
        total_amount=total,
        credit_score=credit_score,
        user_credit_limit=float(current_user.credit_limit or 0),
        available_credit=float(current_user.available_credit),
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

    selected_plan = next(
        (p for p in session.get('bnpl_plans', []) if p.get('months') == months),
        None
    )
    if selected_plan:
        emi = float(selected_plan.get('emi_amount') or selected_plan.get('emi', 0))
        fee = float(selected_plan.get('processing_fee', 0))
    else:
        rate = _get_interest_rate(credit_score, months)
        emi  = _calc_emi(total, rate, months)
        fee  = _processing_fee(total, credit_score)

    today    = date.today()
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
    db.session.flush()

    for i in range(1, months + 1):
        due = today + relativedelta(months=i)
        repayment = Repayment(
            plan_id=plan.id,
            user_id=current_user.id,
            due_date=due,
            amount_due=emi,
        )
        db.session.add(repayment)

    # Log the approved purchase transaction
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
        is_flagged=session.get('fraud_result', {}).get('risk_level') in ('HIGH', 'MEDIUM'),
    )
    db.session.add(txn)
    db.session.commit()

    # Clear session state
    for k in ['cart', 'bnpl_approved', 'credit_score_result', 'fraud_result', 'bnpl_total', 'fraud_block']:
        session.pop(k, None)
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
    return render_template(
        'bnpl/success.html',
        plan=plan,
        repayments=repayments,
        user_credit_limit=float(current_user.credit_limit or 0),
        available_credit=float(current_user.available_credit),
    )


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
    return render_template(
        'bnpl/repayments.html',
        plans=plans,
        repayments=all_repayments,
        user_credit_limit=float(current_user.credit_limit or 0),
        available_credit=float(current_user.available_credit),
    )


@bnpl_bp.route('/pay-emi/<int:repayment_id>', methods=['POST'])
@login_required
def pay_emi(repayment_id):
    repayment = Repayment.query.filter_by(id=repayment_id, user_id=current_user.id).first_or_404()

    if repayment.status == 'paid':
        return jsonify({'success': False, 'message': 'Already paid.'})

    total_due = float(repayment.amount_due) + float(repayment.late_fee)
    repayment.amount_paid = total_due
    repayment.paid_at     = datetime.utcnow()
    repayment.status      = 'paid'

    txn = Transaction(
        user_id=current_user.id,
        amount=total_due,
        product_name=f'EMI Payment – Plan #{repayment.plan_id}',
        category='EMI',
        transaction_type='emi_payment',
        status='approved',
    )
    db.session.add(txn)

    # Check if entire plan is now complete → restore credit (mark plan completed)
    plan = BNPLPlan.query.get(repayment.plan_id)
    if plan:
        remaining = Repayment.query.filter(
            Repayment.plan_id == plan.id,
            Repayment.status  != 'paid',
            Repayment.id      != repayment_id,
        ).count()
        if remaining == 0:
            plan.status = 'completed'
            # Credit automatically restores because available_credit property
            # only sums 'active' plans — marking 'completed' frees the headroom

    db.session.commit()

    # Return updated credit info to frontend
    return jsonify({
        'success': True,
        'message': 'EMI paid successfully.',
        'user_credit_limit': float(current_user.credit_limit or 0),
        'available_credit':  float(current_user.available_credit),
    })
