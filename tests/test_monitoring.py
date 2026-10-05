"""Tests de la supervision /admin/monitoring — Séance S10 (P4)."""
from datetime import datetime, timezone

from app.models import db, User, Worker


def _login(client):
    client.post("/register", data={"username": "admin", "email": "admin@example.com",
                                    "password": "password123"}, follow_redirects=True)
    # l'inscription crée un compte non-admin : on le promeut pour accéder au monitoring
    user = User.query.filter_by(username="admin").first()
    user.is_admin = True
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "password123"},
                follow_redirects=True)


def test_monitoring_requires_login(client):
    resp = client.get("/admin/monitoring")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_monitoring_returns_structure(client, app):
    # un worker en base
    db.session.add(Worker(hostname="worker1", ip="192.168.56.11", status="AVAILABLE",
                          cpu=2, memory=2048, max_instances=10,
                          last_heartbeat=datetime.now(timezone.utc)))
    db.session.commit()

    _login(client)
    resp = client.get("/admin/monitoring")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["services"]["db"] == "up"
    assert "active" in data["instances"]
    assert len(data["workers"]) == 1
    assert data["workers"][0]["hostname"] == "worker1"
    assert data["workers"][0]["status"] == "AVAILABLE"
    assert data["workers"][0]["last_heartbeat"] is not None
