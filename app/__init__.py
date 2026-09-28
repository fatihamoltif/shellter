import os

from flask import Flask
from sqlalchemy import text

from config import config_by_name
from .extensions import db


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)

    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .api import api_bp
    from .workers import workers_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(workers_bp, url_prefix="/workers")

    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok"}, 200
        except Exception:
            return {"status": "unavailable"}, 503

    return app



