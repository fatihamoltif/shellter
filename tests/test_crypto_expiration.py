"""Tests chiffrement (Imen) + expiration (Fatiha), intégrés par P4 — S11."""
from datetime import datetime, timezone, timedelta

import app.expiration_manager as em
from app.models import db, User, Distribution, Worker, Instance, Rental
from app.ssh_credentials import encrypt_password, decrypt_password, reveal_password


# --- chiffrement ---------------------------------------------------------- #
def test_encrypt_decrypt_roundtrip(app):
    enc = encrypt_password("s3cr3t-pw")
    assert enc != "s3cr3t-pw"
    assert decrypt_password(enc) == "s3cr3t-pw"


def test_reveal_tolerates_plaintext(app):
    assert reveal_password("pas-chiffre") == "pas-chiffre"      # ancien secret en clair
    assert reveal_password(encrypt_password("abc")) == "abc"    # secret chiffré


# --- expiration ----------------------------------------------------------- #
def test_expire_due_rentals(app, monkeypatch):
    calls = {"deleted": 0}
    monkeypatch.setattr(em, "delete_container",
                        lambda worker, cid: calls.__setitem__("deleted", calls["deleted"] + 1))

    u = User(username="u", email="u@example.com", password_hash="x")
    w = Worker(hostname="w1", ip="192.168.56.11", status="AVAILABLE", cpu=2,
               memory=2048, max_instances=10, agent_url="http://x:5000",
               last_heartbeat=datetime.now(timezone.utc))
    d = Distribution(name="U", docker_image="ubuntu:24.04", version="24.04", status="enabled")
    db.session.add_all([u, w, d])
    db.session.commit()

    inst = Instance(worker_id=w.id, distribution_id=d.id, ssh_port=20000,
                    ssh_user="shellter", ssh_secret="x", status="running",
                    container_id="c1")
    db.session.add(inst)
    db.session.commit()

    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    r = Rental(user_id=u.id, instance_id=inst.id,
               start_time=past - timedelta(minutes=30), end_time=past, status="ACTIVE")
    db.session.add(r)
    db.session.commit()

    n = em.expire_due_rentals()
    assert n == 1
    assert calls["deleted"] == 1
    db.session.refresh(r)
    db.session.refresh(inst)
    assert r.status == "EXPIRED"
    assert inst.status == "deleted"


def test_active_rental_not_expired(app, monkeypatch):
    monkeypatch.setattr(em, "delete_container", lambda worker, cid: None)
    u = User(username="u", email="u@example.com", password_hash="x")
    w = Worker(hostname="w1", ip="192.168.56.11", status="AVAILABLE", cpu=2,
               memory=2048, max_instances=10, agent_url="http://x:5000",
               last_heartbeat=datetime.now(timezone.utc))
    d = Distribution(name="U", docker_image="ubuntu:24.04", version="24.04", status="enabled")
    db.session.add_all([u, w, d])
    db.session.commit()
    inst = Instance(worker_id=w.id, distribution_id=d.id, ssh_port=20001,
                    ssh_user="shellter", ssh_secret="x", status="running", container_id="c2")
    db.session.add(inst)
    db.session.commit()
    future = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.session.add(Rental(user_id=u.id, instance_id=inst.id,
                          start_time=datetime.now(timezone.utc), end_time=future, status="ACTIVE"))
    db.session.commit()
    assert em.expire_due_rentals() == 0
