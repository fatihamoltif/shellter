"""Tests de résilience — reprise sur un autre worker — Séance S7 (P4).

Scénario prof : une instance tourne sur worker1, worker1 tombe (halt) -> OFFLINE ->
l'instance est recréée sur worker2. L'agent est mocké.
"""
from datetime import datetime, timezone, timedelta

from app.models import db, User, Distribution, Worker, Instance, Rental
from app.recovery import recover_instances, mark_stale_workers_offline


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_worker(hostname, ip, status="AVAILABLE", heartbeat_age_s=0):
    w = Worker(
        hostname=hostname, ip=ip, status=status,
        cpu=2, memory=2048, max_instances=10,
        agent_url=f"http://{ip}:5000",
        last_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=heartbeat_age_s),
    )
    db.session.add(w)
    db.session.commit()
    return w


def make_distro():
    d = Distribution(name="Ubuntu 24.04", docker_image="ubuntu:24.04", version="24.04")
    db.session.add(d)
    db.session.commit()
    return d


def make_user(username="demo", email="demo@example.com"):
    u = User(username=username, email=email, password_hash="x")
    db.session.add(u)
    db.session.commit()
    return u


def make_running_instance(worker, distro, user=None, port=20000):
    user = user or make_user()
    inst = Instance(
        worker_id=worker.id, distribution_id=distro.id, ssh_port=port,
        ssh_user="shellter", ssh_secret="x", status="running", container_id="c-old",
    )
    db.session.add(inst)
    db.session.flush()
    db.session.add(Rental(
        user_id=user.id, instance_id=inst.id,
        end_time=datetime.now(timezone.utc) + timedelta(hours=1), status="ACTIVE",
    ))
    db.session.commit()
    return inst


# --------------------------------------------------------------------------- #
# détection OFFLINE (heartbeat)
# --------------------------------------------------------------------------- #
def test_mark_stale_worker_offline(app):
    w = make_worker("worker1", "192.168.56.11", heartbeat_age_s=120)
    changed = mark_stale_workers_offline()
    assert w.status == "OFFLINE"
    assert w in changed


def test_fresh_worker_stays_available(app):
    w = make_worker("worker1", "192.168.56.11", heartbeat_age_s=0)
    mark_stale_workers_offline()
    assert w.status == "AVAILABLE"


# --------------------------------------------------------------------------- #
# reprise sur un autre worker
# --------------------------------------------------------------------------- #
def test_recover_moves_instance_to_other_worker(app, fake_agent):
    w1 = make_worker("worker1", "192.168.56.11")
    w2 = make_worker("worker2", "192.168.56.12")
    distro = make_distro()
    inst = make_running_instance(w1, distro, port=20000)

    w1.status = "OFFLINE"            # worker1 tombe
    db.session.commit()

    recovered = recover_instances()

    assert len(recovered) == 1
    assert inst.worker_id == w2.id          # reparti sur worker2
    assert inst.status == "running"
    assert inst.container_id != "c-old"      # nouveau conteneur créé par l'agent
    assert fake_agent["created"] == 1


def test_recover_without_target_stays_recovering(app, fake_agent):
    w1 = make_worker("worker1", "192.168.56.11")     # seul worker
    distro = make_distro()
    inst = make_running_instance(w1, distro)

    w1.status = "OFFLINE"
    db.session.commit()

    recovered = recover_instances()

    assert recovered == []
    assert inst.status == "recovering"       # aucun autre worker -> reste recovering


def test_full_scenario_halt_worker1(app, fake_agent):
    """Scénario prof : vagrant halt worker1 -> OFFLINE -> instance repart sur worker2."""
    w1 = make_worker("worker1", "192.168.56.11", heartbeat_age_s=0)
    w2 = make_worker("worker2", "192.168.56.12", heartbeat_age_s=0)
    distro = make_distro()
    inst = make_running_instance(w1, distro, port=20000)

    # worker1 ne donne plus de heartbeat (équivaut à vagrant halt worker1)
    w1.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=120)
    db.session.commit()

    # détection (P1) puis reprise (P4)
    mark_stale_workers_offline()
    assert w1.status == "OFFLINE"

    recover_instances()

    assert inst.worker_id == w2.id           # l'instance repart bien sur worker2
    assert inst.status == "running"
    # l'utilisateur voit le nouveau host dans son dashboard
    assert w2.ip == "192.168.56.12"
