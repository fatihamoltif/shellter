"""Tests d'intégration HTTP — S8.

Ils sont lancés contre la stack docker-compose.ci.yml :
Flask + PostgreSQL + Worker Agent simulé.
"""

import os
import re

import requests


BASE_URL = os.getenv(
    "BASE_URL",
    "http://localhost:8080",
)


def _csrf(session, path):
    """Récupère le token CSRF généré par un formulaire."""

    response = session.get(
        f"{BASE_URL}{path}",
        timeout=10,
    )

    assert response.status_code == 200

    match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        response.text,
    )

    assert match, (
        f"jeton CSRF introuvable sur {path}"
    )

    return match.group(1)


def test_health():
    response = requests.get(
        f"{BASE_URL}/health",
        timeout=10,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"


def test_full_journey_register_login_dashboard_rent():

    session = requests.Session()

    # ---------------------------------------------
    # Inscription
    # ---------------------------------------------

    csrf_token = _csrf(
        session,
        "/register",
    )

    response = session.post(
        f"{BASE_URL}/register",
        data={
            "csrf_token": csrf_token,
            "username": "itest",
            "email": "itest@example.com",
            "password": "password123",
        },
        timeout=10,
    )

    assert response.status_code == 200

    # ---------------------------------------------
    # Connexion
    # ---------------------------------------------

    csrf_token = _csrf(
        session,
        "/login",
    )

    response = session.post(
        f"{BASE_URL}/login",
        data={
            "csrf_token": csrf_token,
            "username": "itest",
            "password": "password123",
        },
        timeout=10,
    )

    assert response.status_code == 200

    # ---------------------------------------------
    # Dashboard
    # ---------------------------------------------

    response = session.get(
        f"{BASE_URL}/dashboard",
        timeout=10,
    )

    assert response.status_code == 200

    assert "itest" in response.text

    # ---------------------------------------------
    # Location
    # ---------------------------------------------

    response = session.post(
        f"{BASE_URL}/rent",
        json={
            "distribution_id": 1,
            "duration_minutes": 30,
        },
        timeout=15,
    )

    assert response.status_code == 201, (
        response.text
    )

    body = response.json()

    assert body["status"] == "running"

    assert body["ssh_command"].startswith(
        "ssh "
    )


def test_dashboard_requires_login():

    response = requests.get(
        f"{BASE_URL}/dashboard",
        allow_redirects=False,
        timeout=10,
    )

    assert response.status_code in (
        301,
        302,
    )

    location = response.headers.get(
        "Location",
        "",
    )

    assert "/login" in location