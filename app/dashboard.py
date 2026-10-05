"""Blueprint du dashboard — Séance S5 (P4).

Page principale après connexion : infos utilisateur, liste des instances (vide pour
l'instant, remplie en S6), boutons « Louer une instance » et « Accéder à mon instance ».
Protégé par login_required : pas de session -> redirection vers /login.
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from .models import Distribution, Rental
from .ssh_credentials import decrypt_password

dashboard_bp = Blueprint("dashboard", __name__)

# Statuts d'instance à ne plus afficher dans « Mes instances ».
_HIDDEN_STATUSES = ("stopped", "error", "deleted")


def _reveal(secret):
    """Déchiffre le mot de passe stocké ; tolère un ancien secret en clair."""
    if not secret:
        return None
    try:
        return decrypt_password(secret)
    except Exception:
        return secret


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
        active_rental = next((r for r in inst.rentals if r.status == "ACTIVE"), None)
        instances.append({
            "id": inst.id,
            "distribution": inst.distribution.name if inst.distribution else "?",
            "status": inst.status,
            "ssh_command": (
                f"ssh {inst.ssh_user}@{worker.ip} -p {inst.ssh_port}"
                if worker and inst.ssh_port else None
            ),
            "password": _reveal(inst.ssh_secret),
            "expires_at": (active_rental.end_time.strftime("%Y-%m-%d %H:%M UTC")
                           if active_rental else None),
        })

    return render_template("dashboard.html", user=current_user,
                           distributions=distributions, instances=instances)
