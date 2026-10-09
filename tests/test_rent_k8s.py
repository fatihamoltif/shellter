"""Test du flux « dashboard -> /rent » en mode Kubernetes (ORCHESTRATOR=k8s).

L'API Kubernetes est MOCKÉE (faux module app.k8s_client) : pas besoin de la lib
kubernetes ni d'un cluster réel. On prouve que la location passe bien par k8s_client
(création d'un env) et que /stop le supprime — c'est le chemin que le bouton « Louer »
du dashboard déclenche sur la branche kubernetes.
"""
import sys
import types

import pytest

from app.models import db, Distribution, Worker


@pytest.fixture()
def fake_k8s(monkeypatch):
    """Injecte un faux app.k8s_client + bascule l'orchestrateur en 'k8s'."""
    calls = {"created": [], "deleted": []}
    fake = types.ModuleType("app.k8s_client")

    class K8sError(Exception):
        pass

    def create_env(image, instance_id, ssh_user, ssh_secret, expires_at=""):
        calls["created"].append(instance_id)
        return {"deployment": f"env-{instance_id}", "nodeport": 31000,
                "node_ip": "192.168.56.12", "container_id": f"env-{instance_id}"}

    def delete_env(instance_id):
        calls["deleted"].append(instance_id)

    fake.K8sError = K8sError
    fake.create_env = create_env
    fake.delete_env = delete_env
    monkeypatch.setitem(sys.modules, "app.k8s_client", fake)

    import app.api as api
    monkeypatch.setattr(api, "ORCHESTRATOR", "k8s")
    return calls


def _distro():
    d = Distribution(name="Ubuntu 24.04", docker_image="ubuntu:24.04",
                     version="24.04", status="enabled")
    db.session.add(d)
    db.session.commit()
    return d


def _register_login(client):
    client.post("/register", data={"username": "demo", "email": "demo@example.com",
                                   "password": "password123"}, follow_redirects=True)
    client.post("/login", data={"username": "demo", "password": "password123"},
                follow_redirects=True)


def test_rent_via_k8s(client, app, fake_k8s):
    distro = _distro()
    _register_login(client)
    r = client.post("/rent", json={"distribution_id": distro.id, "duration_minutes": 30})
    assert r.status_code == 201, r.data
    body = r.get_json()
    assert body["status"] == "running"
    # le SSH pointe sur le NodePort du cluster (pas un worker agent)
    assert body["ssh_command"] == "ssh shellter@192.168.56.12 -p 31000"
    assert body.get("ssh_password")
    assert fake_k8s["created"] == [body["instance_id"]]       # k8s_client.create_env appelé
    # un worker "virtuel" représentant le cluster a été créé
    assert Worker.query.filter_by(hostname="k8s-cluster").first() is not None


def test_stop_via_k8s(client, app, fake_k8s):
    distro = _distro()
    _register_login(client)
    inst = client.post("/rent", json={"distribution_id": distro.id,
                                      "duration_minutes": 30}).get_json()["instance_id"]
    r = client.post(f"/instances/{inst}/stop")
    assert r.status_code == 200
    assert fake_k8s["deleted"] == [inst]                      # k8s_client.delete_env appelé
