from flask import Blueprint, redirect, render_template, url_for, jsonify, request
from flask_login import login_required, current_user

from models.user import User
from models.transaction import Transaction
from models.fraud_log import FraudLog
from models.bnpl_plan import BNPLPlan
from models.repayment import Repayment
from utils.encryption import decrypt_field
from extensions import db

admin_bp = Blueprint('admin', __name__)


def _is_admin():
    """Simple admin check — first registered user (id=1) is admin."""
    return current_user.is_authenticated and current_user.id == 1


@admin_bp.route('/')
@admin_bp.route('')
@login_required
def dashboard():
    if not _is_admin():
        return redirect(url_for('dashboard.home'))

    total_users = User.query.count()
    active_plans = BNPLPlan.query.filter_by(status='active').count()
    flagged_transactions = Transaction.query.filter_by(is_flagged=True).count()
    total_transactions = Transaction.query.count()

    fraud_logs = (
        FraudLog.query
        .order_by(FraudLog.flagged_at.desc())
        .limit(20)
        .all()
    )

    users = User.query.order_by(User.account_created_at.desc()).limit(50).all()
    all_users = []
    for u in users:
        try:
            name  = decrypt_field(u.name_encrypted)
            email = decrypt_field(u.email_encrypted)
        except Exception:
            name, email = '—', '—'
        all_users.append({
            'id':             u.id,
            'name':           name,
            'email':          email,
            'credit_score':   u.credit_score,
            'kyc_status':     u.kyc_status,
            'is_blacklisted': u.is_blacklisted,
            'trust_score':    u.trust_score,
            'city':           u.city or '—',
            'created_at':     u.account_created_at,
            'bnpl_plans':     u.bnpl_plans,
        })

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_plans=active_plans,
        flagged_transactions=flagged_transactions,
        total_transactions=total_transactions,
        fraud_logs=fraud_logs,
        all_users=all_users,
    )


@admin_bp.route('/resolve-log/<int:log_id>', methods=['POST'])
@login_required
def resolve_log(log_id):
    if not _is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    log = FraudLog.query.get_or_404(log_id)
    log.resolved = True
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/blacklist/<int:user_id>', methods=['POST'])
@login_required
def blacklist_user(user_id):
    if not _is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    action = request.json.get('action', 'blacklist')
    user = User.query.get_or_404(user_id)
    user.is_blacklisted = (action == 'blacklist')
    db.session.commit()
    return jsonify({'success': True})
