"""Réconciliateur base ↔ cluster (partie P4, séance K4).

Kubernetes recrée les pods (self-healing) sans prévenir la base. Ce module aligne la
table `instances` sur l'état réel du cluster : une instance dont le pod est en cours de
recréation passe `recovering`, revient `running` quand il est prêt, et passe `deleted`
si son Deployment a disparu.
"""
import logging

from .models import db, Instance
from . import k8s_client

logger = logging.getLogger(__name__)

_RUNNINGISH = ("running", "recovering")


def reconcile():
    """Aligne la base sur l'état du cluster. Retourne le nombre d'instances modifiées."""
    cluster = {e["instance_id"]: e for e in k8s_client.list_envs()}
    changed = 0
    for inst in Instance.query.filter(Instance.status.in_(_RUNNINGISH)).all():
        env = cluster.get(str(inst.id))
        if env is None:                       # plus de Deployment -> disparue
            inst.status = "deleted"
            changed += 1
        elif not env["ready"] and inst.status != "recovering":
            inst.status = "recovering"        # pod en cours de (re)création
            changed += 1
            logger.info("instance %s : pod non prêt -> recovering", inst.id)
        elif env["ready"] and inst.status == "recovering":
            inst.status = "running"           # pod de nouveau prêt
            changed += 1
            logger.info("instance %s : pod rétabli -> running", inst.id)
    if changed:
        db.session.commit()
    return changed
