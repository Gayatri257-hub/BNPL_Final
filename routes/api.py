from datetime import datetime

from flask import Blueprint, jsonify, session
from flask_login import current_user, login_required

from models.transaction import Transaction

api_bp = Blueprint('api', __name__)


@api_bp.route('/activity-feed')
@login_required
def activity_feed():
    transactions = (
        Transaction.query
        .filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_at.desc())
        .limit(5)
        .all()
    )

    activities = []
    for t in transactions:
        activities.append({
            'type':        'transaction',
            'description': f'{t.transaction_type.replace("_", " ").title()}: {t.product_name or "—"}',
            'amount':      float(t.amount),
            'time':        t.transaction_at.strftime('%H:%M'),
            'flagged':     t.is_flagged,
        })

    risk_level = 'LOW' if current_user.trust_score > 70 else 'MEDIUM'

    return jsonify({
        'activities':    activities,
        'risk_level':    risk_level,
        'trust_score':   current_user.trust_score,
        'last_updated':  datetime.utcnow().strftime('%H:%M:%S'),
    })


@api_bp.route('/credit-score')
@login_required
def credit_score_api():
    return jsonify({
        'credit_score': current_user.credit_score,
        'trust_score':  current_user.trust_score,
        'kyc_status':   current_user.kyc_status,
    })


@api_bp.route('/cart-count')
@login_required
def cart_count():
    cart = session.get('cart', [])
    count = sum(item.get('quantity', 0) for item in cart)
    return jsonify({'count': count})
