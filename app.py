import os
from flask import Flask, redirect, render_template, url_for
from config import Config
from extensions import db, login_manager, bcrypt


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ML_MODELS_PATH'], exist_ok=True)

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

    # Create all DB tables on first run
    with app.app_context():
        from models import user, transaction, bnpl_plan, repayment, fraud_log, kyc  # noqa: F401
        db.create_all()

    return app


if __name__ == '__main__':
    application = create_app()
    application.run(debug=True)
