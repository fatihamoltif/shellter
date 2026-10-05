"""Resource Manager — choix du worker pour une location — Séance S6 (P4).

Règle : parmi les workers AVAILABLE dont le heartbeat est récent et qui ont encore de la
capacité, on choisit celui qui héberge le MOINS d'instances actives.
"""
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy import func

from .models import db, Worker, Instance

# Un heartbeat plus vieux que ça => worker considéré injoignable.
# Configurable par variable d'environnement (utile en tests d'intégration).
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "30"))

# Statuts d'instance qui « occupent » réellement un worker.
ACTIVE_INSTANCE_STATUSES = ("pending", "creating", "running", "recovering")

# Plage de ports hôte réservée à l'accès SSH des conteneurs.
SSH_PORT_START = 20000
SSH_PORT_END = 30000


def _active_counts():
    """Nombre d'instances actives par worker : {worker_id: count}."""
    rows = (
        db.session.query(Instance.worker_id, func.count(Instance.id))
        .filter(Instance.status.in_(ACTIVE_INSTANCE_STATUSES))
        .group_by(Instance.worker_id)
        .all()
    )
    return {worker_id: count for worker_id, count in rows}


def select_worker():
    """Retourne le meilleur worker disponible, ou None si aucun.

    Éligible = statut AVAILABLE + heartbeat récent + capacité restante.
    Choisi = celui qui a le moins d'instances actives.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
    counts = _active_counts()

    best, best_count = None, None
    for worker in Worker.query.filter(Worker.status == "AVAILABLE").all():
        # heartbeat récent obligatoire
        if worker.last_heartbeat is None:
            continue
        hb = worker.last_heartbeat
        if hb.tzinfo is None:                 # comparaison sûre si stocké naïf
            hb = hb.replace(tzinfo=timezone.utc)
        if hb < cutoff:
            continue

        count = counts.get(worker.id, 0)
        if worker.max_instances is not None and count >= worker.max_instances:
            continue

        if best is None or count < best_count:
            best, best_count = worker, count

    return best


def pick_free_ssh_port():
    """Retourne un port SSH libre (non utilisé par une instance active), ou None."""
    used = {
        i.ssh_port
        for i in Instance.query.filter(
            Instance.status.in_(ACTIVE_INSTANCE_STATUSES),
            Instance.ssh_port.isnot(None),
        ).all()
    }
    for port in range(SSH_PORT_START, SSH_PORT_END + 1):
        if port not in used:
            return port
    return None


def worker_is_full(worker):
    """True si le worker a atteint sa capacité max (=> passe BUSY)."""
    if worker.max_instances is None:
        return False
    return _active_counts().get(worker.id, 0) >= worker.max_instances