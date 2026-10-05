"""Blueprint worker ↔ controller — enregistrement et heartbeat des workers.

Appelé par les Worker Agents (machine à machine) : pas de session utilisateur,
exempté de CSRF. Un worker qui bat le cœur est (ré)enregistré et son
last_heartbeat rafraîchi ; un worker OFFLINE qui resignale redevient AVAILABLE.
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from .models import db, Worker

worker_bp = Blueprint("worker", __name__)


@worker_bp.route("/workers/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json(silent=True) or {}
    hostname = data.get("hostname")
    if not hostname:
        return jsonify(error="bad_request", message="hostname requis."), 400

    now = datetime.now(timezone.utc)
    worker = Worker.query.filter_by(hostname=hostname).first()

    if worker is None:
        worker = Worker(
            hostname=hostname,
            ip=data.get("ip", ""),
            cpu=data.get("cpu"),
            memory=data.get("memory"),
            max_instances=data.get("max_instances", 10),
            agent_url=data.get("agent_url"),
            status="AVAILABLE",
            last_heartbeat=now,
        )
        db.session.add(worker)
        created = True
    else:
        worker.last_heartbeat = now
        if data.get("ip"):
            worker.ip = data["ip"]
        if data.get("agent_url"):
            worker.agent_url = data["agent_url"]
        # un worker injoignable qui resignale redevient disponible
        if worker.status == "OFFLINE":
            worker.status = "AVAILABLE"
        created = False

    db.session.commit()
    return jsonify(status="ok", worker_id=worker.id, created=created), 200
