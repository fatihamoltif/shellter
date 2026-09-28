"""Fixtures pytest — Séance S4 (P4).

- En CI : DATABASE_URL pointe sur le service PostgreSQL (contraintes FK + CHECK réelles).
- En local sans DATABASE_URL : SQLite en mémoire (rapide), avec les FK activées.
"""
import os

import pytest
from sqlalchemy import event

from app import create_app
from app.models import db


@pytest.fixture()
def app():
    # SQLite en mémoire par défaut si aucune base n'est fournie (tests locaux rapides)
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    application = create_app()
    application.config.update(TESTING=True)

    with application.app_context():
        # SQLite n'applique pas les clés étrangères par défaut : on les active.
        if db.engine.dialect.name == "sqlite":
            @event.listens_for(db.engine, "connect")
            def _enable_sqlite_fk(dbapi_conn, _record):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def session(app):
    """Session SQLAlchemy prête à l'emploi (dans le contexte applicatif)."""
    return db.session
