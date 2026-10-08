"""Runner du réconciliateur (partie P4, séance K4) — appelé par un CronJob."""
import logging

from app import create_app
from app.reconciler import reconcile

logging.basicConfig(level=logging.INFO)


def main():
    app = create_app()
    with app.app_context():
        logging.info("%s instance(s) réconciliée(s)", reconcile())


if __name__ == "__main__":
    main()
