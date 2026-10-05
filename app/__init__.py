"""Application factory Shellter — Séance S5.

create_app assemble : configuration par environnement, base de données, migrations,
Flask-Login (sessions), protection CSRF (Flask-WTF), blueprints, et /health.
"""
import os

from flask import Flask, jsonify, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from sqlalchemy import text

from .models import db, User
from .config import config_by_name

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    # SQLite en mémoire (tests locaux) : une seule connexion partagée, sinon chaque
    # connexion aurait sa propre base vide. Sans effet sur PostgreSQL (CI).
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite") and ":memory:" in uri:
        from sqlalchemy.pool import StaticPool
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"   # redirection si non authentifié
    csrf.init_app(app)                          # protection CSRF sur tous les POST

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .api import api_bp
    from .monitoring import monitoring_bp
    from .admin import admin_bp
    from .workers import worker_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(worker_bp)
    csrf.exempt(api_bp)      # API JSON (clients curl/agent) : pas de jeton CSRF de formulaire
    csrf.exempt(worker_bp)   # heartbeat des agents (machine à machine)

    @app.route("/")
    def index():
        return redirect(url_for("dashboard.index"))

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok", db="up"), 200
        except Exception:
            return jsonify(status="degraded", db="down"), 503

    return app
