from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()






# ===== TEMPORAIRE S5/P3 - DEBUT =====

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ===== TEMPORAIRE S5/P3 - FIN =====
class Worker(db.Model):
    __tablename__ = "workers"

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), unique=True, nullable=False)
    ip = db.Column(db.String(45), nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="AVAILABLE"
    )

    cpu = db.Column(db.Float)
    memory = db.Column(db.Integer)
    last_heartbeat = db.Column(db.DateTime(timezone=True))

    max_instances = db.Column(db.Integer)
    agent_url = db.Column(db.String(255))

    instances = db.relationship(
        "Instance",
        back_populates="worker"
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('AVAILABLE', 'BUSY', 'OFFLINE')",
            name="ck_workers_status"
        ),
    )


class Instance(db.Model):
    __tablename__ = "instances"

    id = db.Column(db.Integer, primary_key=True)

    container_id = db.Column(db.String(255))

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey("workers.id"),
        nullable=False
    )

    distribution_id = db.Column(
        db.Integer,
        db.ForeignKey("distributions.id"),
        nullable=False
    )

    ssh_port = db.Column(db.Integer)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    ssh_user = db.Column(db.String(100))
    ssh_secret = db.Column(db.String(500))

    worker = db.relationship(
        "Worker",
        back_populates="instances"
    )

    distribution = db.relationship("Distribution")

    rentals = db.relationship(
        "Rental",
        back_populates="instance"
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN "
            "('pending', 'creating', 'running', 'recovering', "
            "'stopped', 'deleted', 'error')",
            name="ck_instances_status"
        ),
    )


class Rental(db.Model):
    __tablename__ = "rentals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    instance_id = db.Column(
        db.Integer,
        db.ForeignKey("instances.id"),
        nullable=False
    )

    start_time = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    end_time = db.Column(
        db.DateTime(timezone=True),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ACTIVE"
    )

    user = db.relationship("User")

    instance = db.relationship(
        "Instance",
        back_populates="rentals"
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('ACTIVE', 'EXPIRED', 'CANCELLED')",
            name="ck_rentals_status"
        ),
    )


###not à moi


class Distribution(db.Model):
    __tablename__ = "distributions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    docker_image = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(50), nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="enabled"
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('enabled', 'disabled')",
            name="ck_distributions_status"
        ),
    )