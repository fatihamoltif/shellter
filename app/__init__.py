import os

from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager, login_required

from .models import db, User


migrate = Migrate()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app():
    app = Flask(__name__)

    # ===== TEMPORAIRE S5/P3 - DEBUT =====

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///shellter.db"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ===== TEMPORAIRE S5/P3 - FIN =====

    # ----- VRAIE PARTIE S5/P3 -----

    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    login_manager.login_view = "auth.login"

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .auth import auth
    app.register_blueprint(auth)

    # ===== TEMPORAIRE S5/P3 - DEBUT =====
    # Faux dashboard uniquement pour tester login_required
    @app.route("/dashboard")
    @login_required
    def dashboard():
        return """
            <p>Dashboard protégé</p>

            <form method="post" action="/logout">
                <button type="submit">Logout</button>
            </form>
        """


    # ===== TEMPORAIRE S5/P3 - FIN =====

    return app