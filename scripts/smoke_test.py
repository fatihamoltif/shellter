"""Smoke test post-déploiement — Séance S10 (P4).

Vérifie rapidement, après un déploiement, que l'essentiel répond :
  /health  ->  connexion (register + login)  ->  location minimale (/rent).

Usage :
  BASE_URL=https://shellter.local python scripts/smoke_test.py
Code de sortie : 0 si tout est OK, 1 sinon.
"""
import os
import re
import sys
import random

import requests

BASE = os.getenv("BASE_URL", "http://localhost:8080")
VERIFY = os.getenv("SMOKE_VERIFY_TLS", "false").lower() == "true"   # self-signed en prod


def _csrf(session, path):
    html = session.get(f"{BASE}{path}", verify=VERIFY, timeout=10).text
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)


def main():
    s = requests.Session()

    # 1) santé
    r = s.get(f"{BASE}/health", verify=VERIFY, timeout=10)
    assert r.status_code == 200 and r.json()["status"] == "ok", "health KO"
    print("  OK  /health")

    # 2) connexion (compte unique)
    u = f"smoke{random.randint(1000, 9999)}"
    s.post(f"{BASE}/register", verify=VERIFY, timeout=10,
           data={"csrf_token": _csrf(s, "/register"), "username": u,
                 "email": f"{u}@example.com", "password": "password123"})
    s.post(f"{BASE}/login", verify=VERIFY, timeout=10,
           data={"csrf_token": _csrf(s, "/login"), "username": u, "password": "password123"})
    assert s.get(f"{BASE}/dashboard", verify=VERIFY, timeout=10).status_code == 200, "login KO"
    print("  OK  inscription + connexion")

    # 3) location minimale
    r = s.post(f"{BASE}/rent", verify=VERIFY, timeout=15,
               json={"distribution_id": 1, "duration_minutes": 30})
    assert r.status_code == 201, f"location KO (HTTP {r.status_code})"
    print("  OK  location (/rent -> 201)")

    print("\n[OK] SMOKE TEST REUSSI")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[FAIL] SMOKE TEST ECHOUE : {exc}")
        sys.exit(1)
