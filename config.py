import os
from dotenv import load_dotenv

load_dotenv()


def _build_db_url() -> str:
    """
    Build the database URL with the following priority:
      1. DATABASE_URL env var (Railway may inject this automatically)
      2. Individual PG* vars provided by Railway's Postgres plugin
      3. Local development fallback
    Railway's internal hostname (web.railway.internal) only resolves inside
    the Railway private network — this is correct for production.
    """
    # 1. Prefer a fully-formed DATABASE_URL
    url = os.environ.get('DATABASE_URL', '')
    if url:
        # SQLAlchemy 2.x requires "postgresql://" not "postgres://"
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url

    # 2. Build from individual Railway Postgres variables
    pg_user = os.environ.get('POSTGRES_USER') or os.environ.get('PGUSER', 'postgres')
    pg_pass = os.environ.get('POSTGRES_PASSWORD') or os.environ.get('PGPASSWORD', 'postgres')
    pg_host = os.environ.get('PGHOST', 'localhost')
    pg_port = os.environ.get('PGPORT', '5432')
    pg_db   = os.environ.get('POSTGRES_DB') or os.environ.get('PGDATABASE', 'railway')

    if pg_host != 'localhost':
        # Running on Railway — use the private network URL
        return (
            f"postgresql://{pg_user}:{pg_pass}"
            f"@{pg_host}:{pg_port}/{pg_db}"
        )

    # 3. Local development fallback
    return 'postgresql://postgres:tiger@localhost:5432/smartpay'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'

    SQLALCHEMY_DATABASE_URI = _build_db_url()

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Robust connection pool settings for Railway's cloud Postgres
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,       # Verify connections before use
        'pool_recycle': 280,         # Recycle before Railway's 300s idle timeout
        'pool_size': 5,              # Keep a small pool (Railway free tier limit)
        'max_overflow': 2,           # Allow a small burst above pool_size
        'pool_timeout': 30,          # Wait up to 30s for a free connection
        'connect_args': {
            'connect_timeout': 10,   # TCP connect timeout in seconds
            'application_name': 'SmartPay-BNPL',
        },
    }

    BCRYPT_LOG_ROUNDS = 12
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    ML_MODELS_PATH = os.environ.get('ML_MODELS_PATH', 'ml/saved_models')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    # Routes use raw request.form fields (no FlaskForm), disable global CSRF
    # to prevent Railway 400s that crash Gunicorn workers
    WTF_CSRF_ENABLED = False


