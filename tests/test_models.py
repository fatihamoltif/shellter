"""Tests des modèles — CRUD et contraintes d'intégrité — Séance S4 (P4).

Couvre la preuve attendue : email en double, clé étrangère invalide, plus le CRUD de base.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import db, User, Distribution, Worker, Instance, Rental


# --------------------------------------------------------------------------- #
# CRUD de base
# --------------------------------------------------------------------------- #
def test_create_and_read_user(session):
    session.add(User(
        username="alice",
        email="alice@shellter.local",
        password_hash="x",
    ))
    session.commit()

    user = User.query.filter_by(username="alice").first()
    assert user is not None
    assert user.email == "alice@shellter.local"
    assert user.id is not None


def test_create_distribution_defaults_enabled(session):
    session.add(Distribution(
        name="Ubuntu 24.04",
        docker_image="ubuntu:24.04",
        version="24.04",
    ))
    session.commit()

    distro = Distribution.query.filter_by(name="Ubuntu 24.04").first()
    assert distro.status == "enabled"      # valeur par défaut


# --------------------------------------------------------------------------- #
# Contraintes d'unicité
# --------------------------------------------------------------------------- #
def test_user_email_must_be_unique(session):
    session.add(User(username="bob", email="dup@shellter.local", password_hash="x"))
    session.commit()

    session.add(User(username="bob2", email="dup@shellter.local", password_hash="x"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_user_username_must_be_unique(session):
    session.add(User(username="charlie", email="c1@shellter.local", password_hash="x"))
    session.commit()

    session.add(User(username="charlie", email="c2@shellter.local", password_hash="x"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# --------------------------------------------------------------------------- #
# Contrainte CHECK (statut invalide) — appliquée par SQLite ET PostgreSQL
# --------------------------------------------------------------------------- #
def test_distribution_invalid_status_rejected(session):
    session.add(Distribution(
        name="Bad",
        docker_image="bad:latest",
        version="1",
        status="not-a-valid-status",
    ))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# --------------------------------------------------------------------------- #
# Clé étrangère invalide — vraie contrainte FK
# --------------------------------------------------------------------------- #
def test_instance_invalid_foreign_key_rejected(session):
    # worker_id / distribution_id qui n'existent pas -> violation de FK
    session.add(Instance(
        worker_id=999,
        distribution_id=999,
        status="pending",
    ))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# --------------------------------------------------------------------------- #
# Relations correctes (chaîne complète user -> rental -> instance -> worker/distro)
# --------------------------------------------------------------------------- #
def test_full_rental_chain(session):
    worker = Worker(hostname="w1", ip="192.168.56.11", status="AVAILABLE")
    distro = Distribution(name="Debian 13", docker_image="debian:13", version="13")
    session.add_all([worker, distro])
    session.commit()

    instance = Instance(
        worker_id=worker.id,
        distribution_id=distro.id,
        status="running",
        ssh_port=20011,
    )
    session.add(instance)
    session.commit()

    user = User(username="dave", email="dave@shellter.local", password_hash="x")
    session.add(user)
    session.commit()

    rental = Rental(
        user_id=user.id,
        instance_id=instance.id,
        end_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status="ACTIVE",
    )
    session.add(rental)
    session.commit()

    assert rental.instance.worker.hostname == "w1"
    assert rental.instance.distribution.docker_image == "debian:13"
    assert rental.user.username == "dave"
