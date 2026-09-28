# S4 — Base de données : seed, tests & CI (P4)

## Objectif (prof)
Tables créées, CRUD testé en local.

## Ma partie P4
Écrire le **seed**, les **tests pytest** (CRUD + contraintes) et le **premier pipeline CI**, puis
prouver qu'un test cassé **bloque** la CI.

## Fichiers livrés
- [`scripts/seed.py`](../../scripts/seed.py) — 3 distributions, 1 utilisateur, 1 worker fictif (idempotent).
- [`tests/conftest.py`](../../tests/conftest.py) — fixtures (PostgreSQL en CI, SQLite en local).
- [`tests/test_models.py`](../../tests/test_models.py) — 7 tests : CRUD, unicité, statut `CHECK`, **clé étrangère invalide**.
- [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) — install → PostgreSQL → pytest.
- [`pytest.ini`](../../pytest.ini) — `pythonpath = .`.

## Comment tester
```bash
pip install -r requirements-dev.txt
pytest -v                 # SQLite en mémoire par défaut
python -m scripts.seed    # -> distributions:3 / utilisateurs:1 / workers:1
```

## Preuve obtenue
- **Run vert** 🟢 : CI sur `alijamai` → tests verts sur PostgreSQL.
- **Run rouge** 🔴 : sur une branche jetable, un test cassé → CI en échec (`1 failed, 6 passed`),
  → prouve que le pipeline **bloque** un code défaillant.

## Détails techniques corrigés
- `SQLAlchemy 2.1` bascule le driver postgres sur `psycopg` (v3) → épinglé `SQLAlchemy==2.0.36`.
- `localhost` → IPv6 sur le runner → URL CI en `127.0.0.1`.
- `pytest` (script) n'ajoute pas la racine au `sys.path` → `pytest.ini` avec `pythonpath = .`.
