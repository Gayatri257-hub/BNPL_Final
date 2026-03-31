import os
from flask import Flask, redirect, render_template, url_for, jsonify
from config import Config
from extensions import db, login_manager, bcrypt


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Log the DB URL in use (mask password for security)
    import re
    _db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    _masked = re.sub(r'(:)[^@]+(@)', r'\1****\2', _db_url)
    app.logger.info(f"[SmartPay] Connecting to DB: {_masked}")
    print(f"[SmartPay] Connecting to DB: {_masked}", flush=True)

    # Ensure upload directories exist (ignore errors on read-only filesystems)
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['ML_MODELS_PATH'], exist_ok=True)
    except OSError:
        pass

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # User loader for Flask-Login
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.shop import shop_bp
    from routes.bnpl import bnpl_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(shop_bp,      url_prefix='/shop')
    app.register_blueprint(bnpl_bp,      url_prefix='/bnpl')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(api_bp,       url_prefix='/api')

    # ── Health check (Railway uses this — must NOT require DB) ──
    @app.route('/health')
    def health():
        return jsonify(status='ok'), 200

    # ── Splash / Index routes ──
    @app.route('/splash')
    def splash():
        return render_template('splash.html')

    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.home'))
        return render_template('welcome.html')

    # ── Error handlers ──
    @app.errorhandler(404)
    def not_found(e):
        return render_template('error/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error/500.html'), 500

    # Create all DB tables on first run — retry loop handles Railway startup race
    with app.app_context():
        import time
        from models import user, transaction, bnpl_plan, repayment, fraud_log, kyc  # noqa: F401
        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.create_all()
                print("Database tables created successfully!", flush=True)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"DB connection attempt {attempt + 1} failed: {e}. Retrying in 5 seconds...", flush=True)
                    time.sleep(5)
                else:
                    print(f"Warning: Could not create tables after {max_retries} attempts: {e}", flush=True)
                    print("App will start anyway - tables may already exist", flush=True)

    return app


# Expose `application` at module level so Gunicorn can import it directly
# (Procfile: web: gunicorn app:application)
application = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port, debug=False)

