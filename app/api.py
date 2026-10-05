"""Blueprint API de location — Séance S6 (P4).

Routes : POST /rent, GET /instances, POST /instances/<id>/stop.
Orchestration : Resource Manager choisit un worker -> l'agent crée le conteneur ->
statuts pending -> creating -> running (ou error).
"""
import secrets
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from .models import db, Distribution, Instance, Rental, Worker
from . import agent_client
from .resource_manager import select_worker, pick_free_ssh_port, worker_is_full

api_bp = Blueprint("api", __name__)

ALLOWED_DURATIONS_MINUTES = {30, 60, 120}
SSH_USER = "shellter"


def _instance_payload(instance, worker=None):
    worker = worker or instance.worker
    rental = instance.rentals[-1] if instance.rentals else None
    return {
        "instance_id": instance.id,
        "status": instance.status,
        "distribution": instance.distribution.docker_image if instance.distribution else None,
        "worker": worker.hostname if worker else None,
        "ssh_command": (
            f"ssh {instance.ssh_user}@{worker.ip} -p {instance.ssh_port}"
            if worker and instance.ssh_port else None
        ),
        "expires_at": rental.end_time.isoformat() if rental else None,
    }


@api_bp.route("/rent", methods=["POST"])
@login_required
def rent():
    data = request.get_json(silent=True) or request.form

    # --- validations ---
    try:
        distribution_id = int(data.get("distribution_id"))
        duration = int(data.get("duration_minutes"))
    except (TypeError, ValueError):
        return jsonify(error="bad_request",
                       message="distribution_id et duration_minutes requis (entiers)."), 400

    if duration not in ALLOWED_DURATIONS_MINUTES:
        return jsonify(error="bad_request",
                       message=f"Durée autorisée : {sorted(ALLOWED_DURATIONS_MINUTES)}."), 400

    distro = db.session.get(Distribution, distribution_id)
    if distro is None or distro.status != "enabled":
        return jsonify(error="not_found", message="Distribution inconnue ou désactivée."), 404

    # --- choix du worker (Resource Manager) ---
    worker = select_worker()
    if worker is None:
        return jsonify(error="worker_unavailable",
                       message="Aucun worker disponible."), 503

    port = pick_free_ssh_port()
    if port is None:
        return jsonify(error="no_port_available"), 503

    # --- création instance + rental (pending -> creating) ---
    ssh_secret = secrets.token_urlsafe(16)     # TODO S9 : stocker chiffré
    now = datetime.now(timezone.utc)
    instance = Instance(
        worker_id=worker.id,
        distribution_id=distro.id,
        ssh_port=port,
        ssh_user=SSH_USER,
        ssh_secret=ssh_secret,
        status="creating",
    )
    db.session.add(instance)
    db.session.flush()      # obtient instance.id sans commit

    rental = Rental(
        user_id=current_user.id,
        instance_id=instance.id,
        start_time=now,
        end_time=now + timedelta(minutes=duration),
        status="ACTIVE",
    )
    db.session.add(rental)

    # --- appel à l'agent ---
    try:
        result = agent_client.create_container(
            worker,
            image=distro.docker_image,
            ssh_port=port,
            instance_id=instance.id,
            ssh_user=SSH_USER,
            ssh_secret=ssh_secret,
            expires_at=rental.end_time.isoformat(),
        )
        instance.container_id = result.get("container_id")
        instance.status = "running"
        if worker_is_full(worker):
            worker.status = "BUSY"
        db.session.commit()
    except agent_client.AgentError as exc:
        instance.status = "error"
        rental.status = "CANCELLED"
        db.session.commit()
        return jsonify(error="creation_failed", message=str(exc)), 502

    payload = _instance_payload(instance, worker)
    payload["rental_id"] = rental.id
    return jsonify(payload), 201


@api_bp.route("/instances", methods=["GET"])
@login_required
def list_instances():
    rentals = Rental.query.filter_by(user_id=current_user.id).all()
    instances = {r.instance for r in rentals if r.instance is not None}
    return jsonify([_instance_payload(i) for i in instances]), 200


@api_bp.route("/instances/<int:instance_id>/stop", methods=["POST"])
@login_required
def stop_instance(instance_id):
    instance = db.session.get(Instance, instance_id)
    # 404 aussi si l'instance appartient à un autre utilisateur (on ne révèle rien)
    if instance is None or not _owned_by(instance, current_user):
        return jsonify(error="not_found"), 404

    worker = instance.worker
    if instance.container_id and worker is not None:
        try:
            agent_client.delete_container(worker, instance.container_id)
        except agent_client.AgentError:
            pass   # on continue le nettoyage logique même si l'agent est injoignable

    instance.status = "stopped"
    for rental in instance.rentals:
        if rental.status == "ACTIVE":
            rental.status = "CANCELLED"
    # le worker n'est peut-être plus plein -> il redevient AVAILABLE
    if worker is not None and worker.status == "BUSY" and not worker_is_full(worker):
        worker.status = "AVAILABLE"
    db.session.commit()

    return jsonify(instance_id=instance.id, status="stopped", rental_status="CANCELLED"), 200


def _owned_by(instance, user):
    return any(r.user_id == user.id for r in instance.rentals)
