"""Fixtures pytest — Séances S4 & S5 (P4).

- En CI : DATABASE_URL pointe sur le service PostgreSQL (contraintes FK + CHECK réelles).
- En local sans DATABASE_URL : SQLite en mémoire (rapide), avec les FK activées.
"""
import pytest
from sqlalchemy import event

from app import create_app
from app.models import db


@pytest.fixture()
def app():
    # config "testing" : SQLite mémoire par défaut, CSRF désactivé pour les tests
    application = create_app("testing")

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
def client(app):
    """Client HTTP de test (pour les tests d'accès de la S5)."""
    return app.test_client()


@pytest.fixture()
def session(app):
    """Session SQLAlchemy prête à l'emploi (pour les tests de modèles de la S4)."""
    return db.session
