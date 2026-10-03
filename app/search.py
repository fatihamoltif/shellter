"""FAILLE VOLONTAIRE (branche demo-vuln, S9) — injection SQL.

Ne JAMAIS faire ça : la saisie utilisateur est injectée directement dans la requête.
Doit être bloqué par Semgrep (SAST). Correctif : requête paramétrée / ORM.
"""
from sqlalchemy import text

from .models import db


def search_users(username):
    # vulnérable : f-string dans une requête SQL
    query = text(f"SELECT id, username FROM users WHERE username = '{username}'")
    return db.session.execute(query).all()
