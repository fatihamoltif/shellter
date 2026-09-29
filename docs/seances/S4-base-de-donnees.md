# S4 — Base de données : seed, tests & CI (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P2 / P3+P4
> **Output prof de la séance :** tables créées, CRUD testé en local.

---

## 1. Contexte et objectif

La S4 crée la base de données (5 tables). Ma partie (P4) automatise la **qualité** de cette base :
données de départ, tests automatisés, et le **premier pipeline d'intégration continue (CI)**.

- P1 → Dockerfile Flask + docker-compose · P2 → modèles User/Distribution · P3 → modèles
  Worker/Instance/Rental + migrations · **P4 → seed + tests + CI**.

**Preuve attendue :** un run **vert** et un run **rouge** sur une branche de test (la CI doit
bloquer un code cassé).

---

## 2. Le modèle (rappel)
5 tables reliées par SQLAlchemy : `users`, `distributions`, `workers`, `instances`, `rentals`, avec
des contraintes `CHECK` sur les statuts et des clés étrangères. Ma partie s'appuie dessus (importé
de la branche de P3) pour écrire le seed et les tests.

---

## 3. Ma partie P4 en détail

### 3.1 Le seed (`scripts/seed.py`)
Insère les données de départ, **idempotent** (relançable sans doublon) :
- 3 distributions : Ubuntu 24.04, Debian 13, Alpine ;
- 1 utilisateur `demo` ;
- 1 worker fictif `worker-fake`.
```bash
python -m scripts.seed
# -> distributions : 3 / utilisateurs : 1 / workers : 1
```

### 3.2 Les fixtures (`tests/conftest.py`)
- **En CI** : `DATABASE_URL` pointe sur un **PostgreSQL** réel → contraintes `FK` et `CHECK` testées
  pour de vrai.
- **En local** : **SQLite en mémoire** (rapide). SQLite n'applique pas les FK par défaut → on active
  `PRAGMA foreign_keys=ON`.

### 3.3 Les tests (`tests/test_models.py`) — 7 tests
| Test | Ce qu'il prouve |
|---|---|
| `test_create_and_read_user` | CRUD de base |
| `test_create_distribution_defaults_enabled` | valeur par défaut d'un statut |
| `test_user_email_must_be_unique` | contrainte d'unicité (email) |
| `test_user_username_must_be_unique` | contrainte d'unicité (username) |
| `test_distribution_invalid_status_rejected` | contrainte `CHECK` (statut invalide) |
| `test_instance_invalid_foreign_key_rejected` | **clé étrangère invalide** refusée |
| `test_full_rental_chain` | relations user → rental → instance → worker/distro |

### 3.4 Le pipeline CI (`.github/workflows/ci.yml`)
```
push / pull_request
 └─ job "test" (ubuntu-latest)
      ├─ service PostgreSQL 16 (éphémère, healthcheck)
      ├─ checkout + Python 3.12
      ├─ pip install -r requirements-dev.txt
      └─ pytest -v      ← bloquant : un test rouge = pipeline rouge
```

---

## 4. Comment tester
```bash
pip install -r requirements-dev.txt
pytest -v                 # SQLite en mémoire par défaut
```

### Produire le run rouge (preuve que la CI bloque)
```bash
git checkout -b test/ci-rouge alijamai
# casser un test : assert user.email == "faux@exemple.com"
git commit -am "test: casse volontaire" && git push origin test/ci-rouge
# -> CI rouge, puis on supprime la branche
```

---

## 5. Preuve obtenue
- **Run vert** 🟢 : CI sur `alijamai` → 7 tests verts sur PostgreSQL.
- **Run rouge** 🔴 : branche `test/ci-rouge` → CI en échec :
  ```
  tests/test_models.py::test_create_and_read_user FAILED
  E   AssertionError: assert 'alice@shellter.local' == 'faux@exemple.com'
  ========================= 1 failed, 6 passed =========================
  ```
  → le pipeline **bloque** bien un code cassé (les 6 autres tests passent = la chaîne fonctionne).

---

## 6. Pièges rencontrés (débogage réel de la CI)
La CI a échoué 3 fois avant d'être verte — 3 bugs empilés derrière un « ça marche chez moi » :

1. **`No module named 'psycopg'`** : `flask-sqlalchemy` n'épingle pas SQLAlchemy → l'install fraîche
   a tiré **SQLAlchemy 2.1**, qui change le driver postgres par défaut vers `psycopg` (v3) au lieu de
   `psycopg2`. → **`SQLAlchemy==2.0.36`** épinglé.
2. **`localhost` → IPv6** : sur le runner Linux, `localhost` peut résoudre en `::1` où Postgres
   n'écoute pas. → URL CI en **`127.0.0.1`**.
3. **`No module named 'app'`** : la CI lance `pytest` (script) qui n'ajoute pas la racine au
   `sys.path` ; moi je testais `python -m pytest` (qui l'ajoute). → **`pytest.ini` avec
   `pythonpath = .`**.

> Pour trouver le n°3 il a fallu récupérer les logs de la CI : la connexion Postgres n'était jamais
> atteinte, ça plantait dès l'import.
