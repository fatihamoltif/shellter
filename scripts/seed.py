"""Seed de la base Shellter — Séance S4 (P4).

Insère les données de départ minimales : 3 distributions, 1 utilisateur, 1 worker fictif.
Idempotent : relançable sans créer de doublons.

Usage :
    # depuis la racine du dépôt, avec DATABASE_URL défini (ou SQLite par défaut)
    python -m scripts.seed
"""
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, Distribution, User, Worker


DISTRIBUTIONS = [
    {"name": "Ubuntu 24.04", "docker_image": "ubuntu:24.04", "version": "24.04"},
    {"name": "Debian 13", "docker_image": "debian:13", "version": "13"},
    {"name": "Alpine", "docker_image": "alpine:latest", "version": "latest"},
]


def seed():
    """Crée les tables si besoin et insère les données de départ (sans doublon)."""
    app = create_app()
    with app.app_context():
        db.create_all()

        # 3 distributions
        for d in DISTRIBUTIONS:
            exists = Distribution.query.filter_by(name=d["name"]).first()
            if not exists:
                db.session.add(Distribution(status="enabled", **d))

        # 1 utilisateur de démonstration
        if not User.query.filter_by(username="demo").first():
            db.session.add(User(
                username="demo",
                email="demo@shellter.local",
                password_hash=generate_password_hash("demo1234"),
            ))

        # 1 worker fictif (utile avant que les vrais workers s'enregistrent)
        if not Worker.query.filter_by(hostname="worker-fake").first():
            db.session.add(Worker(
                hostname="worker-fake",
                ip="192.168.56.99",
                status="AVAILABLE",
                cpu=2,
                memory=2048,
                max_instances=10,
                agent_url="http://192.168.56.99:5000",
            ))

        db.session.commit()

        print("Seed terminé :")
        print(f"  distributions : {Distribution.query.count()}")
        print(f"  utilisateurs  : {User.query.count()}")
        print(f"  workers       : {Worker.query.count()}")


if __name__ == "__main__":
    seed()
