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

    # 2) appliquer les migrations versionnées (Flask-Migrate) ; un changement de
    #    schéma ne détruit plus la base. Repli sur create_all() si indisponible.
    try:
        from flask_migrate import upgrade
        upgrade()
    except Exception as exc:
        print(f"[start] migrations indisponibles ({exc}) -> db.create_all()", flush=True)
        db.create_all()

    for name, image, version in DISTROS:
        if not Distribution.query.filter_by(name=name).first():
            db.session.add(Distribution(name=name, docker_image=image,
                                        version=version, status="enabled"))

    if not User.query.filter_by(username="demo").first():
        db.session.add(User(username="demo", email="demo@example.com",
                            password_hash=generate_password_hash("password123")))

    # Compte administrateur (gestion des distributions + monitoring).
    admin = User.query.filter_by(username="admin").first()
    if admin is None:
        db.session.add(User(username="admin", email="admin@example.com",
                            password_hash=generate_password_hash("admin123"),
                            is_admin=True))
    elif not admin.is_admin:
        admin.is_admin = True

    # 3) worker fictif pointant sur l'agent mock (pour que /rent aboutisse en intégration)
    if os.getenv("SEED_MOCK_WORKER") == "1" and not Worker.query.filter_by(hostname="mock").first():
        db.session.add(Worker(
            hostname="mock",
            ip=os.getenv("WORKER_IP", "agent-mock"),          # localhost en stack réelle
            status="AVAILABLE",
            cpu=2, memory=2048, max_instances=10,
            agent_url=os.getenv("AGENT_URL", "http://agent-mock:5000"),
            last_heartbeat=datetime.now(timezone.utc),
        ))

    # Déploiement sur les VM : seed des vrais workers.
    # REAL_WORKERS="worker1:192.168.56.11,worker2:192.168.56.12,worker3:192.168.56.13"
    real = os.getenv("REAL_WORKERS")
    if real:
        for spec in real.split(","):
            host, ip = spec.split(":")
            worker = Worker.query.filter_by(hostname=host).first()
            if worker is None:
                db.session.add(Worker(
                    hostname=host, ip=ip, status="AVAILABLE",
                    cpu=2, memory=2048, max_instances=10,
                    agent_url=f"http://{ip}:5000",
                    last_heartbeat=datetime.now(timezone.utc),
                ))
            else:
                # Redéploiement : rafraîchir pour que le worker soit de nouveau éligible.
                worker.ip = ip
                worker.status = "AVAILABLE"
                worker.agent_url = f"http://{ip}:5000"
                worker.last_heartbeat = datetime.now(timezone.utc)

    # Course possible entre répliques (K8s : 2 pods Flask seedent en parallèle).
    # Une seule insertion gagne ; l'autre attrape le conflit et l'ignore.
    from sqlalchemy.exc import IntegrityError
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        print("[start] seed déjà effectué par une autre réplique -> ignoré", flush=True)

# 4) démarrer le serveur
# --timeout > AGENT_TIMEOUT : le 1er `rent` sur un worker peut builder l'image SSH
# (plusieurs dizaines de secondes) ; sans ça, gunicorn tuerait le worker à 30 s.
gunicorn_timeout = str(int(os.getenv("AGENT_TIMEOUT", "180")) + 20)
os.execvp("gunicorn", ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2",
                       "--timeout", gunicorn_timeout, "wsgi:app"])
