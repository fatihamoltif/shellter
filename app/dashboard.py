"""Blueprint du dashboard — Séance S5 (P4).

Page principale après connexion : infos utilisateur, liste des instances (vide pour
l'instant, remplie en S6), boutons « Louer une instance » et « Accéder à mon instance ».
Protégé par login_required : pas de session -> redirection vers /login.
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    # La vraie liste d'instances arrivera en S6 (route /instances).
    instances = []
    return render_template("dashboard.html", user=current_user, instances=instances)