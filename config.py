import os
from dotenv import load_dotenv

load_dotenv()


def _fix_db_url(url: str) -> str:
    """Railway provides postgres:// but SQLAlchemy 2.x requires postgresql://"""
    if url and url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'
    SQLALCHEMY_DATABASE_URI = _fix_db_url(
        os.environ.get('DATABASE_URL') or 'postgresql://postgres:postgres@localhost:5432/SmartPay'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    BCRYPT_LOG_ROUNDS = 12
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    ML_MODELS_PATH = os.environ.get('ML_MODELS_PATH', 'ml/saved_models')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    # Routes use raw request.form fields (no FlaskForm), disable global CSRF
    # to prevent Railway 400s that crash Gunicorn workers
    WTF_CSRF_ENABLED = False

