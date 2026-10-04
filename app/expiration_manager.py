import logging
from datetime import datetime, timezone

from .models import db, Rental
from .agent_client import delete_container, AgentError


logger = logging.getLogger(__name__)


def expire_due_rentals():
    now = datetime.now(timezone.utc)

    rentals = Rental.query.filter(
        Rental.status == "ACTIVE",
        Rental.end_time <= now,
    ).all()

    expired_count = 0

    for rental in rentals:
        instance = rental.instance

        if instance is None:
            logger.warning(
                "Rental %s sans instance associée",
                rental.id,
            )
            continue

        worker = instance.worker

        try:
            if instance.container_id and worker is not None:
                delete_container(
                    worker,
                    instance.container_id,
                )

            rental.status = "EXPIRED"
            instance.status = "deleted"

            # Une instance vient d'être libérée.
            if worker is not None and worker.status == "BUSY":
                worker.status = "AVAILABLE"

            db.session.commit()
            expired_count += 1

            logger.info(
                "Rental %s expirée - instance %s supprimée",
                rental.id,
                instance.id,
            )

        except AgentError as exc:
            # Si le worker est vraiment inaccessible,
            # on ne prétend pas que le conteneur a été supprimé.
            db.session.rollback()

            logger.error(
                "Agent inaccessible pour rental %s : %s",
                rental.id,
                exc,
            )

        except Exception:
            db.session.rollback()

            logger.exception(
                "Erreur pendant l'expiration de rental %s",
                rental.id,
            )

    return expired_count