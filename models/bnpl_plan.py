from datetime import datetime
from extensions import db


class BNPLPlan(db.Model):
    __tablename__ = 'bnpl_plans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tenure_months = db.Column(db.Integer, nullable=False)
    emi_amount = db.Column(db.Numeric(10, 2), nullable=False)
    processing_fee = db.Column(db.Numeric(10, 2), default=0)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default='active')  # active/completed/defaulted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    repayments = db.relationship('Repayment', backref='plan', lazy=True)
