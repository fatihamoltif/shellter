"""Blueprint API de location — Séance S6 (P4).

Routes : POST /rent, GET /instances, POST /instances/<id>/stop.
Orchestration : Resource Manager choisit un worker -> l'agent crée le conteneur ->
statuts pending -> creating -> running (ou error).
"""
import os
import secrets
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from .models import db, Distribution, Instance, Rental, Worker
from . import agent_client
from .resource_manager import select_worker, pick_free_ssh_port, worker_is_full
from .ssh_credentials import encrypt_password

api_bp = Blueprint("api", __name__)

ALLOWED_DURATIONS_MINUTES = {30, 60, 120}
SSH_USER = "shellter"

# Backend d'orchestration : "agent" (Worker Agent, branche main) ou "k8s" (Kubernetes).
ORCHESTRATOR = os.getenv("ORCHESTRATOR", "agent")


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

    # --- quota par utilisateur ---
    active_rentals = Rental.query.filter_by(
        user_id=current_user.id, status="ACTIVE"
    ).count()
    if active_rentals >= current_user.max_instances:
        return jsonify(
            error="quota_exceeded",
            message=(f"Quota atteint : {current_user.max_instances} instance(s) "
                     "active(s) maximum par utilisateur."),
        ), 403

    # --- orchestration Kubernetes : le scheduler K8s remplace le Resource Manager ---
    if ORCHESTRATOR == "k8s":
        return _rent_k8s(distro, duration)

    # --- choix du worker (Resource Manager) ---
    worker = select_worker()
    if worker is None:
        return jsonify(error="worker_unavailable",
                       message="Aucun worker disponible."), 503

    port = pick_free_ssh_port()
    if port is None:
        return jsonify(error="no_port_available"), 503

    # --- création instance + rental (pending -> creating) ---
    # secret en clair pour le conteneur + remis une fois au client ;
    # stocké CHIFFRÉ au repos (module ssh_credentials d'Imen).
    ssh_secret = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    instance = Instance(
        worker_id=worker.id,
        distribution_id=distro.id,
        ssh_port=port,
        ssh_user=SSH_USER,
        ssh_secret=encrypt_password(ssh_secret),
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
    payload["ssh_password"] = ssh_secret   # credential remis au propriétaire à la création
    return jsonify(payload), 201


# --------------------------------------------------------------------------- #
# Orchestration Kubernetes (branche kubernetes) — remplace agent + resource manager
# --------------------------------------------------------------------------- #
def _cluster_worker():
    """Worker « virtuel » représentant le cluster (le scheduling est délégué à K8s).

    On garde la table workers pour ne pas changer le schéma : toutes les locations K8s
    sont rattachées à ce worker. L'IP sert d'hôte SSH (NodePort est joignable sur
    n'importe quel nœud).
    """
    worker = Worker.query.filter_by(hostname="k8s-cluster").first()
    if worker is None:
        worker = Worker(
            hostname="k8s-cluster",
            ip=os.getenv("NODE_IP_FALLBACK", "192.168.56.10"),
            status="AVAILABLE", cpu=0, memory=0, max_instances=100000,
            agent_url="k8s://", last_heartbeat=datetime.now(timezone.utc),
        )
        db.session.add(worker)
        db.session.commit()
    return worker


def _ssh_image_for(distro):
    img = (distro.docker_image or "").lower()
    if "debian" in img:
        return os.getenv("SSH_IMAGE_DEBIAN", "ghcr.io/fatihamoltif/shellter-ssh-debian:latest")
    if "alpine" in img:
        return os.getenv("SSH_IMAGE_ALPINE", "ghcr.io/fatihamoltif/shellter-ssh-alpine:latest")
    return os.getenv("SSH_IMAGE_UBUNTU", "ghcr.io/fatihamoltif/shellter-ssh-ubuntu:latest")


def _rent_k8s(distro, duration):
    """Loue via Kubernetes : crée un Deployment(1) + Service NodePort pour le SSH."""
    from . import k8s_client     # import tardif : la lib kubernetes n'est utile qu'ici

    worker = _cluster_worker()
    ssh_secret = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)

    instance = Instance(
        worker_id=worker.id, distribution_id=distro.id, ssh_user=SSH_USER,
        ssh_secret=encrypt_password(ssh_secret), status="creating",
    )
    db.session.add(instance)
    db.session.flush()

    rental = Rental(
        user_id=current_user.id, instance_id=instance.id, start_time=now,
        end_time=now + timedelta(minutes=duration), status="ACTIVE",
    )
    db.session.add(rental)

    try:
        result = k8s_client.create_env(
            image=_ssh_image_for(distro),
            instance_id=instance.id,
            ssh_user=SSH_USER,
            ssh_secret=ssh_secret,
            expires_at=rental.end_time.isoformat(),
        )
        instance.ssh_port = result["nodeport"]          # NodePort alloué par K8s
        instance.container_id = result["deployment"]
        worker.ip = result["node_ip"]                   # IP d'un nœud joignable
        instance.status = "running"
        db.session.commit()
    except k8s_client.K8sError as exc:
        instance.status = "error"
        rental.status = "CANCELLED"
        db.session.commit()
        return jsonify(error="creation_failed", message=str(exc)), 502

    payload = _instance_payload(instance, worker)
    payload["rental_id"] = rental.id
    payload["ssh_password"] = ssh_secret
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
    if ORCHESTRATOR == "k8s":
        from . import k8s_client
        try:
            k8s_client.delete_env(instance.id)   # supprime Deployment + Service
        except k8s_client.K8sError:
            pass
    elif instance.container_id and worker is not None:
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


@api_bp.route("/instances/<int:instance_id>/extend", methods=["POST"])
@login_required
def extend_instance(instance_id):
    """Prolonge la location active d'une instance de duration_minutes."""
    data = request.get_json(silent=True) or request.form
    try:
        duration = int(data.get("duration_minutes"))
    except (TypeError, ValueError):
        return jsonify(error="bad_request",
                       message="duration_minutes requis (entier)."), 400
    if duration not in ALLOWED_DURATIONS_MINUTES:
        return jsonify(error="bad_request",
                       message=f"Durée autorisée : {sorted(ALLOWED_DURATIONS_MINUTES)}."), 400

    instance = db.session.get(Instance, instance_id)
    if instance is None or not _owned_by(instance, current_user):
        return jsonify(error="not_found"), 404

    rental = next((r for r in instance.rentals if r.status == "ACTIVE"), None)
    if rental is None:
        return jsonify(error="not_extensible",
                       message="Aucune location active pour cette instance."), 409

    rental.end_time = rental.end_time + timedelta(minutes=duration)
    db.session.commit()
    return jsonify(instance_id=instance.id,
                   expires_at=rental.end_time.isoformat()), 200


def _owned_by(instance, user):
    return any(r.user_id == user.id for r in instance.rentals)
