from datetime import datetime
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name_encrypted = db.Column(db.Text, nullable=False)
    email_encrypted = db.Column(db.Text, nullable=False, unique=True)
    email_hash = db.Column(db.String(255), nullable=False, unique=True)  # for lookup
    phone_encrypted = db.Column(db.Text)
    password_hash = db.Column(db.String(255), nullable=False)
    monthly_income_range = db.Column(db.String(50))
    city = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    account_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    kyc_status = db.Column(db.String(20), default='pending')  # pending/verified/failed
    agreement_signed = db.Column(db.Boolean, default=False)
    agreement_signed_at = db.Column(db.DateTime)
    digital_signature_path = db.Column(db.String(500))
    agreement_pdf_path = db.Column(db.String(500))
    is_blacklisted = db.Column(db.Boolean, default=False)
    credit_score = db.Column(db.Integer, default=0)
    trust_score = db.Column(db.Integer, default=100)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    bnpl_plans = db.relationship('BNPLPlan', backref='user', lazy=True)
    repayments = db.relationship('Repayment', backref='user', lazy=True)
    fraud_logs = db.relationship('FraudLog', backref='user', lazy=True)
    kyc_record = db.relationship('KYCRecord', backref='user', uselist=False, lazy=True)

    def __repr__(self):
        return f'<User {self.id}>'


# ---------------------------------------------------------------------------
# Flask-Login user loader
# ---------------------------------------------------------------------------
from extensions import login_manager  # noqa: E402

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
