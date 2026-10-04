"""Application factory Shellter."""

import os

from flask import Flask, jsonify, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from sqlalchemy import text

from .models import db, User
from .config import config_by_name
from .workers import bp as workers_bp

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    """Recharge un utilisateur depuis son id stocké dans la session."""
    return db.session.get(User, int(user_id))


def create_app(config_name=None):
    """Crée et configure l'application Flask."""

    config_name = config_name or os.getenv(
        "FLASK_CONFIG",
        "development"
    )

    app = Flask(__name__)

    config_class = config_by_name.get(
        config_name,
        config_by_name["development"]
    )

    app.config.from_object(config_class)

    # -------------------------------------------------
    # Configuration temporaire utile en développement
    # -------------------------------------------------

    # Si aucune DATABASE_URL n'est définie en local,
    # on utilise SQLite pour pouvoir démarrer l'application.
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            "sqlite:///shellter.db"
        )

    # SECRET_KEY de secours uniquement en développement.
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = (
            os.getenv(
                "SECRET_KEY",
                "dev-key-a-changer"
            )
        )

    # Cas particulier des tests SQLite en mémoire.
    uri = app.config["SQLALCHEMY_DATABASE_URI"]

    if uri.startswith("sqlite") and ":memory:" in uri:
        from sqlalchemy.pool import StaticPool

        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {
                "check_same_thread": False
            },
            "poolclass": StaticPool,
        }

    # -------------------------------------------------
    # Extensions
    # -------------------------------------------------

    db.init_app(app)

    migrate.init_app(
        app,
        db
    )

    login_manager.init_app(app)

    # Ton blueprint auth utilise l'endpoint "auth.login".
    login_manager.login_view = "auth.login"

    csrf.init_app(app)

    # -------------------------------------------------
    # Blueprints
    # -------------------------------------------------

    # Dans TA branche actuelle, app/auth.py contient :
    # auth = Blueprint("auth", __name__)
    from .auth import auth_bp

    # Ces deux fichiers utilisent déjà *_bp.
    from .dashboard import dashboard_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(workers_bp)

    # L'API reçoit du JSON/curl et ne fonctionne pas
    # comme un formulaire HTML Flask-WTF.
    csrf.exempt(api_bp)
    csrf.exempt(workers_bp)
    # -------------------------------------------------
    # Routes générales
    # -------------------------------------------------

    @app.route("/")
    def index():
        return redirect(
            url_for("dashboard.index")
        )

    @app.get("/health")
    def health():
        try:
            db.session.execute(
                text("SELECT 1")
            )

            return jsonify(
                status="ok",
                db="up"
            ), 200

        except Exception:
            return jsonify(
                status="degraded",
                db="down"
            ), 503

    return app