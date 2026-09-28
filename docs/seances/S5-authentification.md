# S5 — API Web : authentification (P4)

## Objectif (prof)
Login et signup fonctionnels de bout en bout.

## Ma partie P4
Écrire le **dashboard** (infos utilisateur, liste d'instances, boutons Louer/Accéder), activer la
**protection CSRF** (Flask-WTF) et écrire les **tests d'accès**. Pour rendre le tout testable, j'ai
mis en place le flux d'auth complet (factory, register, login/sessions).

## Fichiers livrés
- [`app/__init__.py`](../../app/__init__.py) — factory : config, DB, Flask-Login, CSRF, blueprints, `/health`.
- [`app/config.py`](../../app/config.py) — configs development / testing / production.
- [`app/auth.py`](../../app/auth.py) — `/register`, `/login`, `/logout`.
- [`app/dashboard.py`](../../app/dashboard.py) — `/dashboard` (P4, `login_required`).
- [`app/forms.py`](../../app/forms.py) — formulaires Flask-WTF (CSRF + validation).
- [`app/templates/`](../../app/templates) — base, login, register, dashboard.
- [`tests/test_auth.py`](../../tests/test_auth.py) — 8 tests d'accès.

## Comment tester
```bash
pip install -r requirements-dev.txt
pytest -v          # 15 passed (8 auth + 7 modèles)

# lancer l'appli :
export SECRET_KEY="dev"; export DATABASE_URL="sqlite:///shellter.db"
python -m scripts.seed && flask --app app run
```
> Le validateur d'email refuse les domaines spéciaux (`.local`) → utiliser `@example.com`, etc.

## Preuve obtenue
Parcours **inscription → connexion → dashboard → déconnexion** fonctionnel, **CI verte** (15 tests).
Sécurité : mots de passe hachés, sessions `HttpOnly`, CSRF active, message de login générique.
