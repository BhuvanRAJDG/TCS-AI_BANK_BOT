"""
app/__init__.py
Flask application factory for SentinelBank AI.
"""
import os

from flask import Flask, g, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

from .config import Config

# Load .env from project root (two levels up from this file)
load_dotenv(dotenv_path=os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '.env'
))

# ── Extension singletons (bound to app in create_app) ────────────────────────
db      = SQLAlchemy()
migrate = Migrate()


# ── Factory ───────────────────────────────────────────────────────────────────

def create_app(config_object: object = Config) -> Flask:
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    app.config.from_object(config_object)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)

    # ── Import all models so SQLAlchemy registers their tables ────────────────
    with app.app_context():
        from .models import (  # noqa: F401
            User, CustomerProfile, Account, Transaction, Loan, EMI,
            CreditScore, Insurance, ExpenseSplit, ExpenseSplitParticipant,
            Autopay, Notification, FraudLog, AuditLog, Session,
        )

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .auth import auth_bp
    from .routes import (
        dashboard_bp, transactions_bp, loans_bp, insurance_bp,
        notifications_bp, profile_bp
    )
    from .routes.chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(insurance_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(chat_bp)

    # ── Security headers (applied to every response) ──────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options']  = 'nosniff'
        response.headers['X-Frame-Options']          = 'DENY'
        response.headers['X-XSS-Protection']         = '1; mode=block'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']        = 'geolocation=(), microphone=()'
        if not app.config.get('FLASK_DEBUG'):
            response.headers['Strict-Transport-Security'] = \
                'max-age=31536000; includeSubDomains'
        return response

    # ── CSRF protection for state-changing requests ───────────────────────────
    @app.before_request
    def enforce_csrf():
        """
        For browser-initiated form/AJAX POST/PUT/PATCH/DELETE we expect either:
          - An X-Requested-With: XMLHttpRequest header (AJAX), OR
          - The Content-Type to be application/json (API clients).
        Requests from /auth/* that use cookies are checked here.
        Exempted: GET, HEAD, OPTIONS; requests carrying a Bearer token (API clients).
        """
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return
        if request.headers.get('Authorization', '').startswith('Bearer '):
            return   # API client — CSRF not applicable
        # Allow JSON API requests
        if request.is_json:
            return
        # Allow AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return
        # Block everything else to state-changing endpoints
        if request.path.startswith('/auth/') or request.path.startswith('/api/'):
            return jsonify({'error': 'CSRF check failed.'}), 403

    # ── Populate g.current_user for every request ─────────────────────────────
    @app.before_request
    def load_current_user():
        g.current_user = None
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        if not token:
            token = request.cookies.get('access_token')
        if token:
            try:
                from .security.jwt import decode_token
                payload = decode_token(token)
                if payload.get('type') == 'access':
                    from .models.user import User
                    g.current_user = User.query.get(int(payload['sub']))
            except Exception:
                g.current_user = None

    # ── Session auth guard (protect all application pages and APIs) ───────────
    from flask import redirect

    @app.before_request
    def enforce_auth_guard():
        path = request.path
        # Exclude static assets, health check, and auth endpoints
        if (
            path.startswith('/static/') or
            path.startswith('/auth/') or
            path in ('/health', '/login', '/register', '/otp')
        ):
            return

        if path == '/':
            if g.current_user:
                return redirect('/dashboard')
            return redirect('/login')

        if not g.current_user:
            if path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized — please log in'}), 401
            return redirect('/login')

    # ── Global JSON error handlers ────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'detail': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Unauthorized'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Forbidden'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({'error': 'Too many requests. Slow down.'}), 429

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'CBS Bank AI'}), 200

    # ── Auth page routes (root-level, not under /auth prefix) ─────────────────
    from flask import render_template

    @app.route('/login')
    def login_page():
        if g.current_user:
            return redirect('/dashboard')
        return render_template('pages/login.html')

    @app.route('/register')
    def register_page():
        if g.current_user:
            return redirect('/dashboard')
        return render_template('pages/register.html')

    @app.route('/otp')
    def otp_page():
        return render_template('pages/otp.html')

    return app

