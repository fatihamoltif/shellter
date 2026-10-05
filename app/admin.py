"""Blueprint d'administration — gestion des distributions.

Réservé aux administrateurs (admin_required). Permet de lister, ajouter et
activer/désactiver les distributions proposées à la location, sans passer par
le seed de démarrage.
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)

from .models import db, Distribution
from .permissions import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/distributions", methods=["GET"])
@admin_required
def distributions():
    distros = Distribution.query.order_by(Distribution.id).all()
    return render_template("admin_distributions.html", distributions=distros)


@admin_bp.route("/admin/distributions", methods=["POST"])
@admin_required
def create_distribution():
    name = (request.form.get("name") or "").strip()
    image = (request.form.get("docker_image") or "").strip()
    version = (request.form.get("version") or "").strip()

    if not (name and image and version):
        flash("Nom, image Docker et version sont obligatoires.", "error")
        return redirect(url_for("admin.distributions"))

    if Distribution.query.filter_by(name=name).first():
        flash(f"Une distribution « {name} » existe déjà.", "error")
        return redirect(url_for("admin.distributions"))

    db.session.add(Distribution(name=name, docker_image=image,
                                version=version, status="enabled"))
    db.session.commit()
    flash(f"Distribution « {name} » ajoutée.", "success")
    return redirect(url_for("admin.distributions"))


@admin_bp.route("/admin/distributions/<int:distro_id>/toggle", methods=["POST"])
@admin_required
def toggle_distribution(distro_id):
    distro = db.session.get(Distribution, distro_id)
    if distro is None:
        abort(404)
    distro.status = "disabled" if distro.status == "enabled" else "enabled"
    db.session.commit()
    flash(f"Distribution « {distro.name} » → {distro.status}.", "success")
    return redirect(url_for("admin.distributions"))
