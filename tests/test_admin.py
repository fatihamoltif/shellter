"""Tests des fonctionnalités S11 (P4) : quota, prolongation, rôle admin.

- quota par utilisateur sur /rent
- prolongation /instances/<id>/extend
- séparation utilisateur / administrateur (distributions + monitoring)
L'agent est mocké (fixture fake_agent).
"""
from datetime import datetime, timezone, timedelta

from app.models import db, User, Distribution, Worker, Rental


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_worker(hostname="worker1", ip="192.168.56.11", max_instances=10):
    w = Worker(hostname=hostname, ip=ip, status="AVAILABLE", cpu=2, memory=2048,
               max_instances=max_instances, agent_url=f"http://{ip}:5000",
               last_heartbeat=datetime.now(timezone.utc))
    db.session.add(w)
    db.session.commit()
    return w


def make_distro(name="Ubuntu 24.04", image="ubuntu:24.04", status="enabled"):
    d = Distribution(name=name, docker_image=image, version="24.04", status=status)
    db.session.add(d)
    db.session.commit()
    return d


def register_login(client, username, email, admin=False):
    client.post("/register", data={"username": username, "email": email,
                                   "password": "password123"}, follow_redirects=True)
    if admin:
        u = User.query.filter_by(username=username).first()
        u.is_admin = True
        db.session.commit()
    client.post("/login", data={"username": username, "password": "password123"},
                follow_redirects=True)


# --------------------------------------------------------------------------- #
# quota par utilisateur
# --------------------------------------------------------------------------- #
def test_rent_respects_user_quota(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    # quota réduit à 1 pour aller vite
    u = User.query.filter_by(username="demo").first()
    u.max_instances = 1
    db.session.commit()

    r1 = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30})
    assert r1.status_code == 201
    r2 = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30})
    assert r2.status_code == 403
    assert r2.get_json()["error"] == "quota_exceeded"


def test_quota_freed_after_stop(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    u = User.query.filter_by(username="demo").first()
    u.max_instances = 1
    db.session.commit()

    inst_id = client.post("/rent", json={"distribution_id": distro.id,
                                         "duration_minutes": 30}).get_json()["instance_id"]
    # quota atteint
    assert client.post("/rent", json={"distribution_id": distro.id,
                                      "duration_minutes": 30}).status_code == 403
    # on arrête -> le quota se libère
    client.post(f"/instances/{inst_id}/stop")
    assert client.post("/rent", json={"distribution_id": distro.id,
                                      "duration_minutes": 30}).status_code == 201


# --------------------------------------------------------------------------- #
# prolongation
# --------------------------------------------------------------------------- #
def test_extend_moves_expiration(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    inst_id = client.post("/rent", json={"distribution_id": distro.id,
                                         "duration_minutes": 30}).get_json()["instance_id"]
    before = Rental.query.filter_by(instance_id=inst_id).first().end_time

    resp = client.post(f"/instances/{inst_id}/extend", json={"duration_minutes": 60})
    assert resp.status_code == 200
    after = Rental.query.filter_by(instance_id=inst_id).first().end_time
    assert (after - before) == timedelta(minutes=60)


def test_extend_invalid_duration(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    inst_id = client.post("/rent", json={"distribution_id": distro.id,
                                         "duration_minutes": 30}).get_json()["instance_id"]
    assert client.post(f"/instances/{inst_id}/extend",
                       json={"duration_minutes": 45}).status_code == 400


def test_extend_other_users_instance_404(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "alice", "alice@example.com")
    inst_id = client.post("/rent", json={"distribution_id": distro.id,
                                         "duration_minutes": 30}).get_json()["instance_id"]
    client.post("/logout", follow_redirects=True)
    register_login(client, "bob", "bob@example.com")
    assert client.post(f"/instances/{inst_id}/extend",
                       json={"duration_minutes": 30}).status_code == 404


# --------------------------------------------------------------------------- #
# rôle admin
# --------------------------------------------------------------------------- #
def test_admin_pages_forbidden_for_normal_user(client, app):
    register_login(client, "demo", "demo@example.com")
    assert client.get("/admin/distributions").status_code == 403
    assert client.get("/admin/monitoring").status_code == 403


def test_admin_can_list_distributions(client, app):
    make_distro()
    register_login(client, "boss", "boss@example.com", admin=True)
    assert client.get("/admin/distributions").status_code == 200


def test_admin_can_create_distribution(client, app):
    register_login(client, "boss", "boss@example.com", admin=True)
    resp = client.post("/admin/distributions",
                       data={"name": "Fedora 40", "docker_image": "fedora:40",
                             "version": "40"}, follow_redirects=True)
    assert resp.status_code == 200
    d = Distribution.query.filter_by(name="Fedora 40").first()
    assert d is not None and d.status == "enabled"


def test_admin_can_toggle_distribution(client, app):
    d = make_distro()
    register_login(client, "boss", "boss@example.com", admin=True)
    client.post(f"/admin/distributions/{d.id}/toggle", follow_redirects=True)
    assert db.session.get(Distribution, d.id).status == "disabled"
    client.post(f"/admin/distributions/{d.id}/toggle", follow_redirects=True)
    assert db.session.get(Distribution, d.id).status == "enabled"


def test_disabled_distribution_cannot_be_rented(client, app, fake_agent):
    make_worker()
    d = make_distro(status="disabled")
    register_login(client, "demo", "demo@example.com")
    assert client.post("/rent", json={"distribution_id": d.id,
                                      "duration_minutes": 30}).status_code == 404


def test_dashboard_renders_and_admin_link_conditional(client, app):
    make_distro()
    register_login(client, "demo", "demo@example.com")
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert b"/admin/distributions" not in r.data        # user normal : pas de lien admin
    client.post("/logout", follow_redirects=True)
    register_login(client, "boss", "boss@example.com", admin=True)
    r2 = client.get("/dashboard")
    assert r2.status_code == 200
    assert b"/admin/distributions" in r2.data            # admin : lien visible
