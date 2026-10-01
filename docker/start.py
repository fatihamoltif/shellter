"""Entrypoint d'intégration : attend la base, crée les tables, seed, puis lance gunicorn.

Utilisé par docker-compose.ci.yml pour les tests d'intégration (S8).
"""
import os
import sys
import time
from datetime import datetime, timezone

# Rendre le paquet "app" importable même lancé via `python docker/start.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, Distribution, User, Worker

app = create_app(os.getenv("FLASK_CONFIG", "development"))

DISTROS = [
    ("Ubuntu 24.04", "ubuntu:24.04", "24.04"),
    ("Debian 13", "debian:13", "13"),
    ("Alpine", "alpine:latest", "latest"),
]

with app.app_context():
    # 1) attendre que PostgreSQL soit prêt
    for _ in range(30):
        try:
            db.session.execute(text("SELECT 1"))
            break
        except Exception:
            time.sleep(2)

    # 2) créer les tables + données de départ
    db.create_all()

    for name, image, version in DISTROS:
        if not Distribution.query.filter_by(name=name).first():
            db.session.add(Distribution(name=name, docker_image=image,
                                        version=version, status="enabled"))

    if not User.query.filter_by(username="demo").first():
        db.session.add(User(username="demo", email="demo@example.com",
                            password_hash=generate_password_hash("password123")))

    # 3) worker fictif pointant sur l'agent mock (pour que /rent aboutisse en intégration)
    if os.getenv("SEED_MOCK_WORKER") == "1" and not Worker.query.filter_by(hostname="mock").first():
        db.session.add(Worker(
            hostname="mock", ip="agent-mock", status="AVAILABLE",
            cpu=2, memory=2048, max_instances=10,
            agent_url="http://agent-mock:5000",
            last_heartbeat=datetime.now(timezone.utc),
        ))

    db.session.commit()

# 4) démarrer le serveur
os.execvp("gunicorn", ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "wsgi:app"])
