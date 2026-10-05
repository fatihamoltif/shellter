"""Tests d'accès — authentification & dashboard — Séance S5 (P4).

Couvre la preuve attendue : accès sans session, mauvais mot de passe, logout,
plus le parcours complet inscription -> connexion -> dashboard -> déconnexion.
"""
from app.models import User


# --- helpers ---------------------------------------------------------------- #
def register(client, username="demo", email="demo@example.com", password="password123"):
    return client.post(
        "/register",
        data={"username": username, "email": email, "password": password},
        follow_redirects=True,
    )


def login(client, username="demo", password="password123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# --- tests d'accès ---------------------------------------------------------- #
def test_dashboard_requires_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_full_auth_journey(client):
    # inscription -> connexion -> dashboard
    register(client)
    resp = login(client)
    assert resp.status_code == 200
    assert b"demo" in resp.data                 # le dashboard affiche le nom
    assert "Aucune instance".encode() in resp.data   # liste vide


def test_login_wrong_password(client):
    register(client)
    client.post("/login", data={"username": "demo", "password": "MAUVAIS"},
                follow_redirects=True)
    # pas de session ouverte -> le dashboard redirige encore
    assert client.get("/dashboard").status_code == 302


def test_logout_closes_session(client):
    register(client)
    login(client)
    assert client.get("/dashboard").status_code == 200   # connecté
    client.post("/logout", follow_redirects=True)
    assert client.get("/dashboard").status_code == 302   # déconnecté


# --- validation du register (P2) ------------------------------------------- #
def test_register_duplicate_email_rejected(client, app):
    register(client, username="user1", email="dup@example.com")
    register(client, username="user2", email="dup@example.com")
    assert User.query.filter_by(email="dup@example.com").count() == 1


def test_register_short_password_rejected(client, app):
    register(client, username="shorty", email="shorty@example.com", password="123")
    assert User.query.filter_by(username="shorty").first() is None


def test_password_never_stored_in_clear(client, app):
    register(client)
    user = User.query.filter_by(username="demo").first()
    assert user is not None
    assert user.password_hash != "password123"
    assert user.check_password("password123")


# --- /health (P1) ----------------------------------------------------------- #
def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
