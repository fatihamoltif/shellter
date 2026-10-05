"""Blueprint d'authentification — register / login / logout — Séance S5.

Register (P2) : validation + hachage du mot de passe.
Login / logout / sessions (P3) : Flask-Login.
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from .models import db, User
from .forms import RegisterForm, LoginForm

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Ce nom d'utilisateur est déjà pris.", "error")
        elif User.query.filter_by(email=form.email.data).first():
            flash("Cet email est déjà utilisé.", "error")
        else:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)          # jamais de mot de passe en clair
            db.session.add(user)
            db.session.commit()
            flash("Compte créé. Vous pouvez vous connecter.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("dashboard.index"))
        flash("Identifiants invalides.", "error")      # message générique (sécurité)
    return render_template("login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Vous êtes déconnecté.", "success")
    return redirect(url_for("auth.login"))
