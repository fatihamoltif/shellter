"""Entrypoint d'intégration S8.

Attend PostgreSQL, crée les tables et les données nécessaires aux tests,
puis démarre Gunicorn.
"""

import os
import sys
import time
from datetime import datetime, timezone


# Permet d'importer le package app lorsque le fichier est lancé ainsi :
# python docker/start.py
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, PROJECT_ROOT)


from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, Distribution, User, Worker


app = create_app(
    os.getenv(
        "FLASK_CONFIG",
        "development",
    )
)


DISTROS = [
    (
        "Ubuntu 24.04",
        "ubuntu:24.04",
        "24.04",
    ),
    (
        "Debian 13",
        "debian:13",
        "13",
    ),
    (
        "Alpine",
        "alpine:latest",
        "latest",
    ),
]


with app.app_context():

    # -------------------------------------------------
    # 1. Attendre PostgreSQL
    # -------------------------------------------------

    for attempt in range(30):
        try:
            db.session.execute(
                text("SELECT 1")
            )

            print("PostgreSQL disponible.")
            break

        except Exception:
            db.session.rollback()

            if attempt == 29:
                raise

            time.sleep(2)

    # -------------------------------------------------
    # 2. Créer les tables
    # -------------------------------------------------

    db.create_all()

    # -------------------------------------------------
    # 3. Seed des distributions
    # -------------------------------------------------

    for name, image, version in DISTROS:

        distribution = Distribution.query.filter_by(
            name=name
        ).first()

        if distribution is None:

            distribution = Distribution(
                name=name,
                docker_image=image,
                version=version,
                status="enabled",
            )

            db.session.add(
                distribution
            )

    # -------------------------------------------------
    # 4. Utilisateur de démonstration
    # -------------------------------------------------

    demo_user = User.query.filter_by(
        username="demo"
    ).first()

    if demo_user is None:

        demo_user = User(
            username="demo",
            email="demo@example.com",
            password_hash=generate_password_hash(
                "password123"
            ),
        )

        db.session.add(
            demo_user
        )

    # -------------------------------------------------
    # 5. Worker mock pour la CI
    # -------------------------------------------------

    if os.getenv("SEED_MOCK_WORKER") == "1":

        worker = Worker.query.filter_by(
            hostname="mock"
        ).first()

        if worker is None:

            worker = Worker(
                hostname="mock",
                ip=os.getenv(
                    "WORKER_IP",
                    "agent-mock",
                ),
                status="AVAILABLE",
                cpu=2,
                memory=2048,
                max_instances=10,
                agent_url=os.getenv(
                    "AGENT_URL",
                    "http://agent-mock:5000",
                ),
                last_heartbeat=datetime.now(
                    timezone.utc
                ),
            )

            db.session.add(
                worker
            )

        else:

            worker.status = "AVAILABLE"

            worker.last_heartbeat = datetime.now(
                timezone.utc
            )

    # -------------------------------------------------
    # 6. Workers réels éventuels
    # -------------------------------------------------

    real_workers = os.getenv(
        "REAL_WORKERS"
    )

    if real_workers:

        for spec in real_workers.split(","):

            hostname, ip = spec.split(":")

            worker = Worker.query.filter_by(
                hostname=hostname
            ).first()

            if worker is None:

                worker = Worker(
                    hostname=hostname,
                    ip=ip,
                    status="AVAILABLE",
                    cpu=2,
                    memory=2048,
                    max_instances=10,
                    agent_url=f"http://{ip}:5000",
                    last_heartbeat=datetime.now(
                        timezone.utc
                    ),
                )

                db.session.add(
                    worker
                )

            else:

                worker.ip = ip
                worker.status = "AVAILABLE"

                worker.agent_url = (
                    f"http://{ip}:5000"
                )

                worker.last_heartbeat = (
                    datetime.now(
                        timezone.utc
                    )
                )

    db.session.commit()


# -------------------------------------------------
# 7. Démarrer Gunicorn
# -------------------------------------------------

os.execvp(
    "gunicorn",
    [
        "gunicorn",
        "--bind",
        "0.0.0.0:5000",
        "--workers",
        "2",
        "wsgi:app",
    ],
)