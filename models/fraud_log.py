from datetime import datetime
from extensions import db


class FraudLog(db.Model):
    __tablename__ = 'fraud_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    fraud_type = db.Column(db.String(100))
    fraud_score = db.Column(db.Numeric(5, 4))
    detection_model = db.Column(db.String(50))
    flagged_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text)
