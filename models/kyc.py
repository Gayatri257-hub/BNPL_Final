from datetime import datetime
from extensions import db


class KYCRecord(db.Model):
    __tablename__ = 'kyc_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pan_encrypted = db.Column(db.Text)
    aadhaar_last4 = db.Column(db.String(4))
    selfie_path = db.Column(db.String(500))
    id_document_path = db.Column(db.String(500))
    liveness_score = db.Column(db.Numeric(5, 4))
    deepfake_score = db.Column(db.Numeric(5, 4))
    face_match_score = db.Column(db.Numeric(5, 4))
    verification_status = db.Column(db.String(20), default='pending')
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
