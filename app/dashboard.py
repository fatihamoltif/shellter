"""Blueprint du dashboard — Séance S5 (P4).

Page principale après connexion : infos utilisateur, liste des instances (vide pour
l'instant, remplie en S6), boutons « Louer une instance » et « Accéder à mon instance ».
Protégé par login_required : pas de session -> redirection vers /login.
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from .models import Distribution, Rental

dashboard_bp = Blueprint("dashboard", __name__)

# Statuts d'instance à ne plus afficher dans « Mes instances ».
_HIDDEN_STATUSES = ("stopped", "error")


@dashboard_bp.route("/dashboard")
@login_required
def index():
    distributions = Distribution.query.filter_by(status="enabled").all()

    # Instances encore actives de l'utilisateur (via ses rentals).
    seen = {}
    for rental in Rental.query.filter_by(user_id=current_user.id).all():
        inst = rental.instance
        if inst is None or inst.status in _HIDDEN_STATUSES:
            continue
        seen[inst.id] = inst

    instances = []
    for inst in seen.values():
        worker = inst.worker
        instances.append({
            "id": inst.id,
            "distribution": inst.distribution.name if inst.distribution else "?",
            "status": inst.status,
            "ssh_command": (
                f"ssh {inst.ssh_user}@{worker.ip} -p {inst.ssh_port}"
                if worker and inst.ssh_port else None
            ),
            "password": inst.ssh_secret,
        })

    return render_template("dashboard.html", user=current_user,
                           distributions=distributions, instances=instances)
