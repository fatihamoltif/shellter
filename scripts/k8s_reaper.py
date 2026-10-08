"""Reaper d'expiration (partie P3, séance K4) — version Kubernetes.

Exécuté périodiquement par un CronJob (k8s/expiration-cronjob.yaml). Supprime, pour
chaque location échue, le Deployment + Service K8s, puis met la base à jour
(rental -> EXPIRED, instance -> deleted). Équivalent K8s de expiration_manager.
"""
import logging
from datetime import datetime, timezone

from app import create_app
from app.models import db, Rental
from app import k8s_client

logging.basicConfig(level=logging.INFO)


def reap_once():
    now = datetime.now(timezone.utc)
    expired = Rental.query.filter(
        Rental.status == "ACTIVE", Rental.end_time <= now).all()
    count = 0
    for rental in expired:
        inst = rental.instance
        try:
            if inst is not None:
                k8s_client.delete_env(inst.id)
                inst.status = "deleted"
            rental.status = "EXPIRED"
            db.session.commit()
            count += 1
            logging.info("rental %s expiré -> env supprimé", rental.id)
        except Exception:
            db.session.rollback()
            logging.exception("échec d'expiration du rental %s", rental.id)
    return count


def main():
    app = create_app()
    with app.app_context():
        logging.info("%s location(s) expirée(s)", reap_once())


if __name__ == "__main__":
    main()
