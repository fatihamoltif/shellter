# Séance S6 — Location d'instances : Resource Manager & API (P4)

> **Auteur : Jamai Ali (P4)**
>
> Ce guide explique **ce qu'on a fait en S6** (la mécanique de location : choisir un worker, créer
> l'instance et la location, piloter l'agent) et **comment la tester**, avec le *pourquoi* de chaque
> choix. **Preuve attendue** : deux locations en parallèle obtiennent des ports distincts, et la
> location d'un autre utilisateur renvoie 404.

---

## 1. Ma partie P4 dans la S6

| Élément | Fichier | Ce que ça fait |
|---|---|---|
| **Resource Manager** | `app/resource_manager.py` | Choisit **où** déployer : worker `AVAILABLE`, heartbeat récent, capacité restante, **le moins chargé**. Attribue un port SSH libre. |
| **API de location** | `app/api.py` | `POST /rent`, `GET /instances`, `POST /instances/<id>/stop`. |
| **Couture vers l'agent** | `app/agent_client.py` | Appelle l'API du Worker Agent (P3) ; mockée dans les tests. |
| **Tests** | `tests/test_rent.py` | 13 tests : Resource Manager + parcours de location + contrôle d'accès. |

---

## 2. Comment marche une location

```
POST /rent
   │  1. valide (utilisateur connecté, distribution enabled, durée autorisée)
   │  2. Resource Manager -> choisit le worker le moins chargé (heartbeat récent)
   │  3. attribue un port SSH libre + génère des credentials
   │  4. crée l'Instance (creating) et le Rental (ACTIVE)
   │  5. appelle l'agent du worker -> crée le conteneur
   │  6. Instance -> running   (ou -> error si l'agent échoue, Rental -> CANCELLED)
   ▼
201  { instance_id, rental_id, status, ssh_command, expires_at }
```

### Règles du Resource Manager
- **Éligible** = `status = AVAILABLE` **et** heartbeat < 30 s **et** capacité restante.
- **Choisi** = le worker qui héberge le **moins d'instances actives**.
- Si le worker atteint `max_instances` après la création → il passe **BUSY**.
- Statuts d'instance « actifs » (occupent un worker) : `pending, creating, running, recovering`.

### Les routes
| Méthode | Route | Accès | Réponses |
|---|---|---|---|
| POST | `/rent` | connecté | `201` créée / `400` params / `404` distro / `503` aucun worker |
| GET | `/instances` | connecté | `200` — **seulement les siennes** |
| POST | `/instances/<id>/stop` | propriétaire | `200` stoppée / **`404`** si pas à lui |

---

## 3. La « couture » vers l'agent (pourquoi c'est mockable)

Flask ne parle **jamais** directement au démon Docker : il appelle l'**API de l'agent** du worker
(`app/agent_client.py` → `POST {agent_url}/containers`). L'agent réel est la partie de **P3**.

Pour tester `/rent` **sans vrai conteneur**, les tests remplacent `agent_client.create_container`
et `delete_container` par des fonctions factices (`monkeypatch`). On teste ainsi toute
l'orchestration Flask (validation, choix du worker, états, ports) de façon isolée et rapide.

---

## 4. Lancer les tests

```bash
pip install -r requirements-dev.txt
pytest -v
```
Attendu : **28 passed** — 13 location (S6) + 8 auth (S5) + 7 modèles (S4).

### Preuves attendues S6 (couvertes par les tests)
- `test_two_parallel_rentals_get_distinct_ports` → **deux locations = deux ports distincts**.
- `test_stop_other_users_instance_returns_404` → **l'instance d'un autre → 404**.
- `test_instances_lists_only_own` → chacun ne voit que ses instances.
- `test_rent_no_worker_available` → `503` si aucun worker.
- `test_rent_invalid_duration` / `test_rent_unknown_distribution` → `400` / `404`.
- `test_select_worker_picks_least_loaded` / `_skips_full_worker` / `_ignores_stale_heartbeat`.
- `test_stop_own_instance` → conteneur supprimé (agent), instance `stopped`, rental `CANCELLED`.

---

## 5. Essai manuel (curl) une fois l'infra prête

```bash
# après login (cookie de session), avec un worker enregistré et une distro seedée :
curl -X POST http://127.0.0.1:5000/rent \
     -H "Content-Type: application/json" \
     -b cookies.txt \
     -d '{"distribution_id": 1, "duration_minutes": 30}'
# -> { "status": "running", "ssh_command": "ssh shellter@192.168.56.11 -p 20000", ... }
```
> L'API est **exemptée de CSRF** (JSON, appelée par curl/l'agent), contrairement aux formulaires web.

---

## 6. Ce qu'il reste pour le TEST MVP #1 (fin de séance)
Le parcours réel *inscription → connexion → location Ubuntu → SSH → Alpine sur un autre worker →
stop* nécessite :
- l'**agent réel** de P3 (`POST /containers` qui lance vraiment le conteneur),
- les **images SSH** de P1 (Ubuntu/Debian/Alpine avec `openssh-server`),
- des **workers enregistrés** (P2, `POST /workers/register` + heartbeat).

Ma partie (Resource Manager + `/rent` + `/instances` + stop) est prête et branchée sur la couture
agent : dès que l'agent de P3 est là, on remplace le mock par l'appel réel, sans changer ma logique.

---

## 7. Note d'intégration
Cette logique vit dans une structure plate (`app/api.py`) sur `alijamai`. P1 a restructuré en
packages (`app/api/`, `app/workers/`). Le Resource Manager et `/rent` sont **indépendants de la
forme** : ils se replaceront dans le package `api` lors de la fusion sur `main`.
