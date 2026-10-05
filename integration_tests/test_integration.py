"""Tests d'intégration end-to-end — Séance S8 (P4).

Lancés contre la stack réelle (docker compose : Flask + PostgreSQL + agent mock),
via de vraies requêtes HTTP. Ne sont PAS collectés par `pytest` normal (hors de
`tests/`) : la CI les lance explicitement avec `pytest integration_tests/`.
"""
import os
import re

import requests

BASE = os.getenv("BASE_URL", "http://localhost:8080")


def _csrf(session, path):
    """Récupère le jeton CSRF caché dans un formulaire (register/login)."""
    html = session.get(f"{BASE}{path}").text
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, f"jeton CSRF introuvable sur {path}"
    return m.group(1)


def test_health():
    r = requests.get(f"{BASE}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_full_journey_register_login_dashboard_rent():
    s = requests.Session()

    # inscription (formulaire + CSRF)
    r = s.post(f"{BASE}/register",
               data={"csrf_token": _csrf(s, "/register"),
                     "username": "itest", "email": "itest@example.com",
                     "password": "password123"},
               timeout=10)
    assert r.status_code == 200

    # connexion
    r = s.post(f"{BASE}/login",
               data={"csrf_token": _csrf(s, "/login"),
                     "username": "itest", "password": "password123"},
               timeout=10)
    assert r.status_code == 200

    # dashboard protégé -> accessible une fois connecté
    r = s.get(f"{BASE}/dashboard", timeout=10)
    assert r.status_code == 200
    assert "itest" in r.text

    # location (API JSON, exemptée de CSRF)
    r = s.post(f"{BASE}/rent",
               json={"distribution_id": 1, "duration_minutes": 30},
               timeout=15)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "running"
    assert body["ssh_command"].startswith("ssh ")


def test_dashboard_requires_login():
    # sans session -> redirection vers /login
    r = requests.get(f"{BASE}/dashboard", allow_redirects=False, timeout=10)
    assert r.status_code in (301, 302)
    assert "/login" in r.headers.get("Location", "")
