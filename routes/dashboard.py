from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from models.bnpl_plan import BNPLPlan
from models.repayment import Repayment
from models.transaction import Transaction
from utils.encryption import decrypt_field

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/home')
@login_required
def home():
    if current_user.kyc_status != 'verified':
        return redirect(url_for('auth.kyc'))
    if not current_user.agreement_signed:
        return redirect(url_for('auth.agreement'))

    user_name = decrypt_field(current_user.name_encrypted)

    transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_at.desc())
        .limit(10)
        .all()
    )

    active_plans = BNPLPlan.query.filter_by(
        user_id=current_user.id, status='active'
    ).all()

    pending_repayments = (
        Repayment.query.filter_by(user_id=current_user.id, status='pending')
        .order_by(Repayment.due_date.asc())
        .all()
    )

    total_due = sum(
        float(r.amount_due) + float(r.late_fee) for r in pending_repayments
    )

    return render_template(
        'dashboard/home.html',
        user_name=user_name,
        transactions=transactions,
        active_plans=active_plans,
        pending_repayments=pending_repayments,
        total_due=total_due,
    )
