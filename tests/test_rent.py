"""Tests de la location — Resource Manager + /rent + /instances + stop — S6 (P4).

L'agent est mocké : on teste l'orchestration Flask sans vrai conteneur Docker.
"""
from datetime import datetime, timezone, timedelta

import pytest

from app.models import db, Distribution, Worker, Instance, Rental
from app import agent_client
from app.resource_manager import select_worker


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_worker(hostname="worker1", ip="192.168.56.11", max_instances=10,
                heartbeat_age_s=0, status="AVAILABLE"):
    w = Worker(
        hostname=hostname, ip=ip, status=status,
        cpu=2, memory=2048, max_instances=max_instances,
        agent_url=f"http://{ip}:5000",
        last_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=heartbeat_age_s),
    )
    db.session.add(w)
    db.session.commit()
    return w


def make_distro(name="Ubuntu 24.04", image="ubuntu:24.04", status="enabled"):
    d = Distribution(name=name, docker_image=image, version="24.04", status=status)
    db.session.add(d)
    db.session.commit()
    return d


def register_login(client, username, email):
    client.post("/register", data={"username": username, "email": email,
                                    "password": "password123"}, follow_redirects=True)
    client.post("/login", data={"username": username, "password": "password123"},
                follow_redirects=True)


# --------------------------------------------------------------------------- #
# Resource Manager (logique pure)
# --------------------------------------------------------------------------- #
def test_select_worker_none_when_no_worker(app):
    assert select_worker() is None


def test_select_worker_ignores_stale_heartbeat(app):
    make_worker(heartbeat_age_s=120)          # heartbeat trop vieux
    assert select_worker() is None


def test_select_worker_picks_least_loaded(app):
    w1 = make_worker("worker1", "192.168.56.11")
    w2 = make_worker("worker2", "192.168.56.12")
    distro = make_distro()
    # 2 instances actives sur w1, 0 sur w2 -> on doit choisir w2
    for _ in range(2):
        db.session.add(Instance(worker_id=w1.id, distribution_id=distro.id, status="running"))
    db.session.commit()
    assert select_worker().hostname == "worker2"


def test_select_worker_skips_full_worker(app):
    make_worker("worker1", "192.168.56.11", max_instances=1)
    distro = make_distro()
    db.session.add(Instance(worker_id=1, distribution_id=distro.id, status="running"))
    db.session.commit()
    assert select_worker() is None            # plein -> aucun dispo


# --------------------------------------------------------------------------- #
# POST /rent
# --------------------------------------------------------------------------- #
def test_rent_requires_login(client):
    assert client.post("/rent", json={"distribution_id": 1, "duration_minutes": 30}).status_code in (302, 401)


def test_rent_success(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    resp = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "running"
    assert body["ssh_command"].startswith("ssh shellter@192.168.56.11 -p ")
    assert fake_agent["created"] == 1


def test_rent_invalid_duration(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    resp = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 45})
    assert resp.status_code == 400


def test_rent_unknown_distribution(client, app, fake_agent):
    make_worker()
    register_login(client, "demo", "demo@example.com")
    resp = client.post("/rent", json={"distribution_id": 999, "duration_minutes": 30})
    assert resp.status_code == 404


def test_rent_no_worker_available(client, app, fake_agent):
    distro = make_distro()                    # aucun worker créé
    register_login(client, "demo", "demo@example.com")
    resp = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30})
    assert resp.status_code == 503


def test_two_parallel_rentals_get_distinct_ports(client, app, fake_agent):
    make_worker("worker1", "192.168.56.11")
    make_worker("worker2", "192.168.56.12")
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    p1 = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30}).get_json()["ssh_command"]
    p2 = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30}).get_json()["ssh_command"]
    port1 = p1.rsplit("-p ", 1)[1]
    port2 = p2.rsplit("-p ", 1)[1]
    assert port1 != port2
    assert Instance.query.count() == 2


# --------------------------------------------------------------------------- #
# contrôle d'accès : instance d'un autre utilisateur -> 404
# --------------------------------------------------------------------------- #
def test_stop_other_users_instance_returns_404(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    # utilisateur A crée une instance
    register_login(client, "alice", "alice@example.com")
    inst_id = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30}).get_json()["instance_id"]
    client.post("/logout", follow_redirects=True)
    # utilisateur B tente de l'arrêter
    register_login(client, "bob", "bob@example.com")
    assert client.post(f"/instances/{inst_id}/stop").status_code == 404


def test_stop_own_instance(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "demo", "demo@example.com")
    inst_id = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30}).get_json()["instance_id"]
    resp = client.post(f"/instances/{inst_id}/stop")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "stopped"
    assert fake_agent["deleted"] == 1
    # rental passé CANCELLED
    assert Rental.query.filter_by(instance_id=inst_id).first().status == "CANCELLED"


def test_instances_lists_only_own(client, app, fake_agent):
    make_worker()
    distro = make_distro()
    register_login(client, "alice", "alice@example.com")
    client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30})
    client.post("/logout", follow_redirects=True)
    register_login(client, "bob", "bob@example.com")
    assert client.get("/instances").get_json() == []   # bob n'a rien
