# S8 — Déploiement complet & CI : tests d'intégration (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P2 / P3+P4
> **Output prof de la séance :** pipeline vert, stack qui démarre en une commande.

---

## 1. Contexte et objectif

La S8 industrialise le déploiement et fait grandir le pipeline. Ma partie (P4) : les **tests
d'intégration en CI** — lancer la **stack complète** (via docker compose) et tester les **vrais
endpoints HTTP**, contrairement aux tests unitaires qui utilisent une base de test isolée.

- P1 → étapes lint & tests · P2 → build des images · P3 → compose final + Nginx · **P4 → tests
  d'intégration en CI**.

**Preuve attendue :** une **étape d'intégration distincte**, verte, qui passe au **rouge si on casse
`/rent`**.

---

## 2. Unitaire vs intégration — la différence

| | Tests unitaires (S4–S7) | Tests d'intégration (S8) |
|---|---|---|
| Quoi | une fonction / une route isolée | **toute la stack ensemble** |
| Base | SQLite/PostgreSQL de test | **le vrai PostgreSQL** du compose |
| Agent | **mocké** (monkeypatch) | **agent mock en conteneur** (HTTP réel) |
| Appel | `client.get()` (en mémoire) | **vraie requête HTTP** (`requests`) |
| But | la logique est correcte | **les composants se parlent bien** |

---

## 3. Ce que j'ai mis en place

### 3.1 La stack d'intégration (`docker-compose.ci.yml`)
Trois conteneurs :
- **`db`** — PostgreSQL 16 (avec healthcheck).
- **`agent-mock`** — simule l'API du Worker Agent (`docker/agent_mock.py`) : répond à
  `POST /containers` → `{container_id}`, sans vrai Docker (l'agent réel est la partie de P3).
- **`web`** — Flask servi par **gunicorn**, lancé par `docker/start.py` qui **attend la base**,
  **crée les tables**, **seed** (3 distros, user `demo`, un worker pointant vers l'agent mock).

### 3.2 Les fichiers support
- `wsgi.py` — point d'entrée gunicorn (`gunicorn wsgi:app`).
- `docker/Dockerfile` — image Flask (Python 3.12, user non-root).
- `docker/start.py` — init (attente DB + `create_all` + seed) puis `exec gunicorn`.
- `docker/agent_mock.py` — l'agent mock.
- `.dockerignore` — exclut `.vagrant`, `.git`, etc. du contexte de build.

### 3.3 Les tests (`integration_tests/test_integration.py`)
De vraies requêtes HTTP contre la stack (port 8080), avec gestion du **jeton CSRF** des formulaires :
- `test_health` → `/health` = 200 ;
- `test_full_journey...` → **inscription → connexion → dashboard → `/rent` (201 + ssh_command)** ;
- `test_dashboard_requires_login` → `/dashboard` sans session → redirection.

> Ces tests sont dans `integration_tests/` (hors de `tests/`) → le `pytest` normal ne les collecte
> pas ; la CI les lance explicitement avec `pytest integration_tests/`.

### 3.4 Le pipeline (`.github/workflows/ci.yml`)
Un **job `integration` distinct**, qui ne tourne **que si les tests unitaires passent** (`needs: test`) :
```
checkout → docker compose up -d --build → attendre /health → pytest integration_tests/
         → (si échec) docker compose logs en ARTEFACT téléchargeable → down
```

---

## 4. Comment tester en local
```bash
docker compose -f docker-compose.ci.yml up -d --build
# attendre quelques secondes, puis :
pip install -r requirements-dev.txt
pytest integration_tests/ -v          # -> 3 passed
docker compose -f docker-compose.ci.yml down -v
```

---

## 5. Preuve obtenue
- **Validé en local** : `3 passed` — le parcours **register → login → dashboard → `/rent` (201)**
  fonctionne de bout en bout sur la vraie stack docker compose.
- **CI** : deux jobs — `test` (unitaires) **puis** `integration` (docker compose), tous les deux verts.
- Si on casse `/rent` (ex. mauvais code retour), le test `test_full_journey` échoue → le **job
  d'intégration passe au rouge**, et les **logs compose sont publiés en artefact**.

---

## 6. Notes d'intégration
- Le `agent-mock` remplace l'agent réel de P3 pour l'intégration — à substituer par le vrai agent
  quand il sera prêt.
- Mon `docker-compose.ci.yml` est dédié à la CI ; il cohabite avec le `docker-compose.yml` final de
  P3 (Nginx + restart policy) sans le remplacer.
- `HEARTBEAT_TIMEOUT_SECONDS` est devenu configurable (env) pour que le worker seedé reste « frais »
  pendant le test d'intégration.
