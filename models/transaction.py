from datetime import datetime
from extensions import db


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    product_name = db.Column(db.String(255))
    category = db.Column(db.String(100))
    transaction_type = db.Column(db.String(50))  # purchase/emi_payment/refund
    transaction_at = db.Column(db.DateTime, default=datetime.utcnow)
    fraud_score = db.Column(db.Numeric(5, 4), default=0)
    is_flagged = db.Column(db.Boolean, default=False)
    fraud_reason = db.Column(db.String(500))
    status = db.Column(db.String(30), default='pending')  # pending/approved/rejected/flagged

    def to_dict(self):
        return {
            'id': self.id,
            'amount': float(self.amount),
            'product_name': self.product_name,
            'category': self.category,
            'transaction_type': self.transaction_type,
            'transaction_at': self.transaction_at.isoformat(),
            'fraud_score': float(self.fraud_score),
            'is_flagged': self.is_flagged,
            'status': self.status
        }
