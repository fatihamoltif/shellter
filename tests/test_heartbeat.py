"""Tests du heartbeat worker -> controller — S11 (P4)."""
from datetime import datetime, timezone, timedelta

from app.models import db, Worker


def test_heartbeat_registers_new_worker(client, app):
    r = client.post("/workers/heartbeat", json={
        "hostname": "worker1", "ip": "192.168.56.11",
        "agent_url": "http://192.168.56.11:5000", "max_instances": 10})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok" and body["created"] is True
    w = Worker.query.filter_by(hostname="worker1").first()
    assert w is not None
    assert w.status == "AVAILABLE"
    assert w.last_heartbeat is not None
    assert w.agent_url == "http://192.168.56.11:5000"


def test_heartbeat_updates_and_revives_offline_worker(client, app):
    w = Worker(hostname="worker1", ip="192.168.56.11", status="OFFLINE",
               cpu=2, memory=2048, max_instances=10,
               agent_url="http://192.168.56.11:5000",
               last_heartbeat=datetime.now(timezone.utc) - timedelta(hours=1))
    db.session.add(w)
    db.session.commit()
    old = w.last_heartbeat

    r = client.post("/workers/heartbeat", json={"hostname": "worker1", "ip": "192.168.56.11"})
    assert r.status_code == 200 and r.get_json()["created"] is False
    db.session.refresh(w)
    assert w.status == "AVAILABLE"          # OFFLINE -> revient AVAILABLE
    assert w.last_heartbeat > old


def test_heartbeat_requires_hostname(client, app):
    assert client.post("/workers/heartbeat", json={}).status_code == 400
