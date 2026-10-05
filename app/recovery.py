"""Résilience — reprise des instances d'un worker en panne — Séance S7 (P4).

Quand un worker passe OFFLINE, ses instances actives sont recréées sur un autre worker
choisi par le Resource Manager. L'utilisateur retrouve dans son dashboard le nouveau host
et le nouveau port.
"""
from datetime import datetime, timezone, timedelta

from .models import db, Worker
from .resource_manager import (
    select_worker,
    pick_free_ssh_port,
    HEARTBEAT_TIMEOUT_SECONDS,
)
from . import agent_client
from .ssh_credentials import reveal_password

# Instances qu'on tente de récupérer quand leur worker tombe.
RECOVERABLE_STATUSES = ("running", "recovering")


def _aware(dt):
    """Rend un datetime timezone-aware (UTC) pour comparaison sûre."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def mark_stale_workers_offline():
    """Passe OFFLINE les workers sans heartbeat récent. Retourne la liste modifiée.

    (Logique de détection heartbeat ; sera portée par l'endpoint /workers/heartbeat de P1.
    Incluse ici pour pouvoir déclencher et tester la reprise de bout en bout.)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
    changed = []
    for worker in Worker.query.filter(Worker.status != "OFFLINE").all():
        hb = _aware(worker.last_heartbeat)
        if hb is None or hb < cutoff:
            worker.status = "OFFLINE"
            changed.append(worker)
    if changed:
        db.session.commit()
    return changed


def _active_rental_end(instance):
    for rental in instance.rentals:
        if rental.status == "ACTIVE":
            return rental.end_time
    return None


def recover_instances():
    """Recrée sur un autre worker les instances actives des workers OFFLINE.

    Retourne la liste des instances effectivement récupérées.
    """
    recovered = []
    for offline in Worker.query.filter_by(status="OFFLINE").all():
        for instance in list(offline.instances):
            if instance.status not in RECOVERABLE_STATUSES:
                continue

            # 1) marquer l'instance "recovering"
            instance.status = "recovering"
            db.session.commit()

            # 2) choisir un AUTRE worker (les OFFLINE sont exclus par le Resource Manager)
            target = select_worker()
            if target is None or target.id == offline.id:
                continue   # aucun worker disponible -> l'instance reste "recovering"

            # 3) recréer le conteneur sur le nouveau worker (durée de location préservée)
            port = pick_free_ssh_port()
            end = _active_rental_end(instance)
            try:
                result = agent_client.create_container(
                    target,
                    image=instance.distribution.docker_image,
                    ssh_port=port,
                    instance_id=instance.id,
                    ssh_user=instance.ssh_user,
                    # secret stocké chiffré -> on le déchiffre pour le conteneur recréé
                    ssh_secret=reveal_password(instance.ssh_secret),
                    expires_at=end.isoformat() if end else "",
                )
            except agent_client.AgentError:
                instance.status = "error"
                db.session.commit()
                continue

            # 4) mettre à jour l'instance -> l'utilisateur voit le nouveau host/port
            #    (via GET /instances et le dashboard)
            instance.worker_id = target.id
            instance.ssh_port = port
            instance.container_id = result.get("container_id")
            instance.status = "running"
            db.session.commit()
            recovered.append(instance)

    return recovered
