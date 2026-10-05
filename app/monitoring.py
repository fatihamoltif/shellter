"""Blueprint de supervision — Séance S10 (P4).

/admin/monitoring : nombre d'instances actives, état + dernier heartbeat de chaque
worker, santé des services. (Accès restreint : login requis ; le rôle admin sera
ajouté plus tard — pour l'instant toute session connectée peut consulter.)
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import func, text

from .models import db, Worker, Instance
from .resource_manager import ACTIVE_INSTANCE_STATUSES

monitoring_bp = Blueprint("monitoring", __name__)


@monitoring_bp.route("/admin/monitoring")
@login_required
def monitoring():
    # santé des services
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"

    # instances
    active = Instance.query.filter(
        Instance.status.in_(ACTIVE_INSTANCE_STATUSES)
    ).count()
    by_status = dict(
        db.session.query(Instance.status, func.count(Instance.id))
        .group_by(Instance.status)
        .all()
    )

    # workers
    workers = []
    for w in Worker.query.all():
        workers.append({
            "hostname": w.hostname,
            "ip": w.ip,
            "status": w.status,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
            "instances": Instance.query.filter(
                Instance.worker_id == w.id,
                Instance.status.in_(ACTIVE_INSTANCE_STATUSES),
            ).count(),
        })

    return jsonify({
        "services": {"flask": "up", "db": db_status},
        "instances": {"active": active, "by_status": by_status},
        "workers": workers,
    }), 200
