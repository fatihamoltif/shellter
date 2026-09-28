# Séance S4 — Base de données : seed, tests & CI (P4)

> **Auteur : Jamai Ali (P4)**
>
> Ce guide explique **ce que j'ai fait en S4** (données de test, tests automatisés, pipeline
> d'intégration continue) et **comment le tester / vérifier**, avec le *pourquoi* de chaque étape.

---

## 1. Ce qu'on a fait en S4 (partie P4)

La S4 met en place la base de données. Ma partie (P4) automatise la **qualité** de cette base :

| Fichier | Rôle |
|---|---|
| `scripts/seed.py` | Insère les **données de départ** : 3 distributions (Ubuntu 24.04, Debian 13, Alpine), 1 utilisateur, 1 worker fictif. Idempotent (relançable sans doublon). |
| `tests/conftest.py` | **Fixtures pytest** : construit l'app + une base de test (PostgreSQL en CI, SQLite en mémoire en local). |
| `tests/test_models.py` | **7 tests** : CRUD, unicité (email/username), statut invalide (contrainte `CHECK`), **clé étrangère invalide**, chaîne complète des relations. |
| `.github/workflows/ci.yml` | Le **pipeline CI** : à chaque push/PR → installe les dépendances → démarre un PostgreSQL → lance `pytest`. |
| `pytest.ini` | Config pytest (`pythonpath = .` pour que `import app` marche partout). |
| `requirements.txt` / `requirements-dev.txt` | Dépendances applicatives / de test. |

> Les modèles (`app/models.py`) et l'app factory (`app/__init__.py`) viennent de P2/P3 : ma partie
> **teste** leur travail, elle ne le réécrit pas.

**Preuve attendue par la prof** : *un run vert et un run rouge sur une branche de test* → voir §5.

---

## 2. Comment marchent les tests

### La base de test (conftest.py)
- **En CI** : la variable `DATABASE_URL` pointe sur un **PostgreSQL** réel (le même moteur qu'en prod)
  → les contraintes `FK` et `CHECK` sont testées pour de vrai.
- **En local sans configuration** : **SQLite en mémoire** (rapide, aucune installation).
  SQLite n'applique pas les clés étrangères par défaut, donc `conftest.py` active
  `PRAGMA foreign_keys=ON` pour que le test de FK soit valable en local aussi.

### Ce que chaque test prouve
- `test_create_and_read_user` / `test_create_distribution_defaults_enabled` → le **CRUD** de base.
- `test_user_email_must_be_unique` / `test_user_username_must_be_unique` → les **contraintes d'unicité**.
- `test_distribution_invalid_status_rejected` → la contrainte **CHECK** sur les statuts.
- `test_instance_invalid_foreign_key_rejected` → une **clé étrangère invalide** est refusée.
- `test_full_rental_chain` → les **relations** user → rental → instance → worker/distribution.

---

## 3. Lancer les tests en local

### Option A — rapide (SQLite, aucune base à installer)
```bash
pip install -r requirements-dev.txt
pytest -v            # utilise SQLite en mémoire par défaut
```
Attendu : `7 passed`.

### Option B — comme la CI (PostgreSQL via Docker)
```bash
# 1) démarrer un PostgreSQL identique à la CI
docker run -d --name shellter-pg \
  -e POSTGRES_USER=shellter -e POSTGRES_PASSWORD=shellter -e POSTGRES_DB=shellter_test \
  -p 5432:5432 postgres:16-alpine

# 2) pointer les tests dessus et lancer
export DATABASE_URL="postgresql://shellter:shellter@127.0.0.1:5432/shellter_test"
pytest -v

# 3) nettoyer
docker rm -f shellter-pg
```
> **Pourquoi `127.0.0.1` et pas `localhost`** : sur Linux, `localhost` peut résoudre en IPv6 (`::1`)
> alors que Postgres n'écoute qu'en IPv4 → connexion refusée. `127.0.0.1` force l'IPv4.

## 4. Lancer le seed
```bash
# SQLite local (crée shellter.db) :
python -m scripts.seed
# ou vers PostgreSQL :
DATABASE_URL="postgresql://shellter:shellter@127.0.0.1:5432/shellter_test" python -m scripts.seed
```
Attendu : `distributions : 3 / utilisateurs : 1 / workers : 1`.

---

## 5. Comment tester / vérifier la CI

La CI se déclenche **automatiquement** à chaque `push` et `pull_request`. On la voit dans
l'onglet **Actions** du dépôt GitHub.

### 5.1 Le run VERT (le code marche)
Il suffit de pousser sur `alijamai` : la CI installe les dépendances, démarre PostgreSQL, lance
`pytest` → **7 passed** → coche verte ✅. C'est le fonctionnement nominal.

### 5.2 Le run ROUGE (prouver que la CI bloque un code cassé)
On casse **volontairement** un test sur une **branche jetable**, pour montrer que le pipeline
refuse le code défaillant :
```bash
git checkout -b test/ci-rouge alijamai

# casser un test : dans tests/test_models.py, mettre une valeur fausse
#   assert user.email == "faux@exemple.com"   # au lieu de "alice@shellter.local"

git commit -am "test: casse volontaire (demo run rouge)"
git push origin test/ci-rouge
```
→ Dans l'onglet Actions, la CI de `test/ci-rouge` passe au **rouge** ❌ avec :
```
tests/test_models.py::test_create_and_read_user FAILED
E   AssertionError: assert 'alice@shellter.local' == 'faux@exemple.com'
========================= 1 failed, 6 passed =========================
```
Puis on nettoie :
```bash
git checkout alijamai
git push origin --delete test/ci-rouge
git branch -D test/ci-rouge
```

> **Ce que ça prouve** : un code cassé **n'atteint jamais** `main` (la CI bloque le merge). C'est
> exactement la « preuve attendue » de la S4 : *un run vert et un run rouge*.

---

## 6. Anatomie du pipeline (`.github/workflows/ci.yml`)

```
push / pull_request
   └─ job "test" (ubuntu-latest)
        ├─ service PostgreSQL 16 (éphémère, avec healthcheck)
        ├─ checkout du code
        ├─ installe Python 3.12
        ├─ pip install -r requirements-dev.txt
        └─ pytest -v   ← bloquant : si un test échoue, le pipeline est rouge
```

## 7. Pièges rencontrés (et corrigés) — pour mémoire
- **`SQLAlchemy 2.1`** bascule le driver Postgres par défaut sur `psycopg` (v3) → on épingle
  `SQLAlchemy==2.0.36` (compatible `psycopg2-binary`).
- **`localhost`** → IPv6 sur le runner : on utilise `127.0.0.1` dans l'URL de la CI.
- **`pytest` (script) n'ajoute pas la racine au `sys.path`** → `ModuleNotFoundError: app` : réglé
  par `pytest.ini` avec `pythonpath = .`.
