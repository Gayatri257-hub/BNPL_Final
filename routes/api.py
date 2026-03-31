import os
from datetime import datetime

from flask import Blueprint, jsonify, request, session
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


# ── SmartBot AI ──────────────────────────────────────────────────────────────

SMARTPAY_CONTEXT = """You are SmartBot, the AI assistant for SmartPay — an AI-powered BNPL (Buy Now Pay Later) platform.

SmartPay Key Facts:
- Uses Logistic Regression for credit scoring (92.6% accuracy), scores range 300-900
- Uses Isolation Forest + Random Forest for fraud detection
- Uses KNN + Decision Tree ensemble for EMI optimization (98% accuracy)
- KYC uses OpenCV deepfake detection and liveness scoring
- All PII encrypted with Fernet AES-256 encryption
- Digital signatures stored as PNG, agreements as PDF
- Database: PostgreSQL with 6 tables (users, transactions, bnpl_plans, repayments, fraud_logs, kyc_records)
- Stack: Python Flask backend, HTML/CSS/JS frontend
- EMI options: 3 months (0% fee for score>=750), 6 months (2% fee), 9 months (3% fee)
- Credit approved if score >= 550
- Built by: Shrutika Giri, Gayatri Badgujar, Anvi Kore at PVG COEM Pune

Answer questions about SmartPay, BNPL, fintech, and financial literacy. Keep responses concise (2-4 sentences), friendly, use emojis occasionally. If asked something completely unrelated to finance/fintech/the app, politely redirect."""


def get_rule_based_response(message):
    """Keyword-based fallback used when Anthropic API key is absent or call fails."""
    m = message.lower()
    if any(w in m for w in ['hi', 'hello', 'hey', 'namaste']):
        return "Namaste! 👋 I'm SmartBot. Ask me about credit scores, EMI plans, fraud protection, or how SmartPay works!"
    if any(w in m for w in ['credit', 'score', 'eligible']):
        return "Your credit score (300-900) is calculated using Logistic Regression analysing income, payment history, KYC status, and account age. Score above 550 gets you approved! 📊"
    if any(w in m for w in ['fraud', 'safe', 'security']):
        return "SmartPay uses Isolation Forest ML + Random Forest to detect fraud in real-time. All data is AES-256 encrypted. 🛡"
    if any(w in m for w in ['emi', 'installment', 'split', 'pay']):
        return "Choose 3, 6, or 9 month EMI plans. Excellent credit (750+) gets 0% processing fee on 3-month plans! 📅"
    if any(w in m for w in ['kyc', 'verification', 'identity']):
        return "KYC uses OpenCV deepfake detection and liveness scoring. Takes under 2 minutes with your Aadhaar and PAN card. 🔍"
    return "I can help with credit scores, EMI plans, fraud protection, KYC, and how SmartPay works! What would you like to know? 😊"


@api_bp.route('/smartbot', methods=['POST'])
def smartbot():
    import requests as req
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'reply': 'Please type a message!'})

    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        return jsonify({'reply': get_rule_based_response(user_message)})

    try:
        response = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 300,
                'system': SMARTPAY_CONTEXT,
                'messages': [{'role': 'user', 'content': user_message}],
            },
            timeout=10,
        )
        result = response.json()
        reply = result['content'][0]['text']
        return jsonify({'reply': reply})
    except Exception:
        return jsonify({'reply': get_rule_based_response(user_message)})
