"""Utilitaire de DÉMO uniquement.

Recule la date de fin des locations ACTIVE dans le passé, pour déclencher
immédiatement l'expiration (le CronJob shellter-reaper les supprime au tick suivant,
≤ 1 min). Pratique pour montrer l'expiration automatique sans attendre 30 min.

Usage (dans le cluster) :
    kubectl -n shellter exec deploy/flask -- python scripts/backdate_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta

from app import create_app
from app.models import db, Rental

app = create_app()
with app.app_context():
    n = 0
    for rental in Rental.query.filter_by(status="ACTIVE").all():
        rental.end_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        n += 1
    db.session.commit()
    print(f"{n} location(s) datee(s) dans le passe -> expiration au prochain tick du reaper")
