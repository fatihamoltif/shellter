from flask import Blueprint, request, redirect, url_for
from flask_login import login_user, logout_user, login_required

from .models import User


auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        return "Identifiants incorrects", 401

    return """
        <form method="post">
            <input name="email" type="email">
            <input name="password" type="password">
            <button type="submit">Login</button>
        </form>
    """


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))