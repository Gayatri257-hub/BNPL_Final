import os
from dotenv import load_dotenv

load_dotenv()

import os as _os

_db_url = _os.environ.get('DATABASE_URL', '') or _os.environ.get('DATABASE_PUBLIC_URL', '')

if not _db_url:
    _pguser = _os.environ.get('PGUSER', _os.environ.get('POSTGRES_USER', 'postgres'))
    _pgpass = _os.environ.get('PGPASSWORD', _os.environ.get('POSTGRES_PASSWORD', 'tiger'))
    _pghost = _os.environ.get('PGHOST', _os.environ.get('RAILWAY_PRIVATE_DOMAIN', 'localhost'))
    _pgport = _os.environ.get('PGPORT', '5432')
    _pgdb = _os.environ.get('PGDATABASE', _os.environ.get('POSTGRES_DB', 'smartpay'))
    _db_url = f'postgresql://{_pguser}:{_pgpass}@{_pghost}:{_pgport}/{_pgdb}'

if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

import os as _os2
_is_railway = bool(_os2.environ.get('RAILWAY_ENVIRONMENT') or _os2.environ.get('RAILWAY_PROJECT_ID'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'

    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 30,
        'pool_size': 5,
        'max_overflow': 2,
        'connect_args': {'sslmode': 'require', 'connect_timeout': 10} if _is_railway else {'connect_timeout': 10}
    }

    BCRYPT_LOG_ROUNDS = 12
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    ML_MODELS_PATH = os.environ.get('ML_MODELS_PATH', 'ml/saved_models')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    # Routes use raw request.form fields (no FlaskForm), disable global CSRF
    # to prevent Railway 400s that crash Gunicorn workers
    WTF_CSRF_ENABLED = False
