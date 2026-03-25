from datetime import datetime
from extensions import db


class Repayment(db.Model):
    __tablename__ = 'repayments'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('bnpl_plans.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount_due = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0)
    paid_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending/paid/overdue/partial
    late_fee = db.Column(db.Numeric(10, 2), default=0)
