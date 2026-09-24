# Shellter — Contrat d'API (v1)

> **Auteur :** P4 · **Séance :** S1 (Cadrage) · **Statut :** contrat figé v1, à faire évoluer par PR.
>
> Ce document est la référence unique des routes HTTP. Toute divergence entre le code et ce
> fichier est un bug : on corrige le code **ou** on met à jour ce document par PR.

---

## 1. Conventions générales

- **Base URL (dev)** : `http://localhost` (via Nginx → Flask). En prod : `https://<controller>` (S10).
- **Format des corps** : formulaires HTML (`application/x-www-form-urlencoded`) pour les pages
  navigateur (`/register`, `/login`, `/rent`…) ; **JSON** (`application/json`) pour les routes
  machine (`/workers/*`, API de l'agent).
- **Encodage** : UTF-8.

### 1.1 Authentification et accès

| Niveau d'accès | Mécanisme | Utilisé par |
|---|---|---|
| `public` | aucun | `/health`, `/register`, `/login` |
| `connecté` | cookie de session Flask-Login (`HttpOnly`, `Secure` en prod) | dashboard, location |
| `propriétaire` | connecté **et** propriétaire de la ressource | `/instances/{id}/stop` |
| `admin` | rôle admin en session | `/admin/monitoring`, liste des workers |
| `token agent` | en-tête `Authorization: Bearer <AGENT_TOKEN>` | `/workers/register`, `/workers/heartbeat` |

### 1.2 Codes HTTP utilisés

| Code | Signification dans Shellter |
|---|---|
| `200 OK` | succès (lecture ou action synchrone) |
| `201 Created` | ressource créée (instance, compte via API) |
| `302 Found` | redirection après action navigateur (login OK, rent OK) |
| `400 Bad Request` | paramètre manquant / invalide (durée, distribution inconnue) |
| `401 Unauthorized` | non connecté / token agent absent ou faux |
| `403 Forbidden` | connecté mais pas les droits (ressource d'un autre / pas admin) |
| `404 Not Found` | ressource inexistante **ou** appartenant à un autre utilisateur |
| `409 Conflict` | doublon (username / email déjà pris) |
| `422 Unprocessable` | validation métier échouée (mot de passe trop court) |
| `503 Service Unavailable` | dépendance HS (base injoignable sur `/health`) |

### 1.3 Format d'erreur (routes JSON)

```json
{ "error": "worker_unavailable", "message": "Aucun worker disponible pour la location." }
```

### 1.4 Énumérations (rappel du modèle — voir docs/db.md de P3)

- **distributions.status** : `enabled`, `disabled`
- **workers.status** : `AVAILABLE`, `BUSY`, `OFFLINE`
- **instances.status** : `pending`, `creating`, `running`, `recovering`, `stopped`, `deleted`, `error`
- **rentals.status** : `ACTIVE`, `EXPIRED`, `CANCELLED`

---

## 2. Santé

### `GET /health` — *public*
État de Flask et de la base.

- **Réponse `200`** : `{ "status": "ok", "db": "up" }`
- **Réponse `503`** : `{ "status": "degraded", "db": "down" }`  *(base arrêtée)*

---

## 3. Authentification

### `GET /register` — *public*
Affiche le formulaire d'inscription.
- **`200`** : page HTML.

### `POST /register` — *public*
Crée un compte.

| Champ | Type | Règle |
|---|---|---|
| `username` | string | unique, 3–32 caractères |
| `email` | string | email valide, unique |
| `password` | string | ≥ 8 caractères |

- **`302`** → `/login` (compte créé, mot de passe **haché**, jamais stocké en clair).
- **`409`** : username ou email déjà pris (message affiché).
- **`422`** : validation échouée (email invalide, mot de passe trop court).

### `GET /login` — *public*
Affiche le formulaire de connexion. **`200`**.

### `POST /login` — *public*
Ouvre une session.

| Champ | Type |
|---|---|
| `username` (ou `email`) | string |
| `password` | string |

- **`302`** → `/dashboard` (session ouverte).
- **`401`** : identifiants invalides (message générique, sans préciser lequel).

### `POST /logout` — *connecté*
Ferme la session.
- **`302`** → `/login`.

---

## 4. Dashboard et instances (utilisateur)

### `GET /dashboard` — *connecté*
Page principale après connexion : infos utilisateur, liste de **ses** instances (statut, date
d'expiration, commande SSH), boutons « Louer une instance » et « Accéder à mon instance ».
- **`200`** : page HTML.
- **`302`** → `/login` si non connecté.

### `GET /instances` — *connecté*
Liste **uniquement** les instances de l'utilisateur courant.
- **`200`** :
```json
[
  { "id": 12, "distribution": "ubuntu:24.04", "status": "running",
    "ssh_command": "ssh user@192.168.56.11 -p 20012",
    "expires_at": "2026-09-24T18:30:00Z", "worker": "worker1" }
]
```

### `POST /instances/{id}/stop` — *propriétaire*
Arrêt anticipé d'une instance : conteneur détruit, rental passé `CANCELLED`.
- **`200`** : `{ "id": 12, "status": "stopped", "rental_status": "CANCELLED" }`
- **`404`** : instance inexistante **ou** appartenant à un autre utilisateur.

---

## 5. Location

### `POST /rent` — *connecté*
Loue une distribution : choisit un worker (Resource Manager), crée l'instance + le rental,
demande le conteneur à l'agent.

| Champ | Type | Règle |
|---|---|---|
| `distribution_id` | int | doit exister et être `enabled` |
| `duration_minutes` | int | valeur parmi une liste autorisée (ex. 30 / 60 / 120) |

**Déroulé des statuts** : `pending → creating → running` (ou `→ error` en cas d'échec).

- **`201`** :
```json
{ "instance_id": 12, "rental_id": 8, "status": "running",
  "ssh_command": "ssh user@192.168.56.11 -p 20012",
  "expires_at": "2026-09-24T18:30:00Z" }
```
- **`400`** : `distribution_id` ou `duration_minutes` manquant / invalide.
- **`404`** : distribution inconnue ou `disabled`.
- **`503`** : `{ "error": "worker_unavailable" }` — aucun worker `AVAILABLE`.

---

## 6. Workers (supervision & agents)

### `GET /workers` — *admin*
Liste des workers et de leur état.
- **`200`** :
```json
[ { "id": 1, "hostname": "worker1", "ip": "192.168.56.11", "status": "AVAILABLE",
    "cpu": 2, "memory": 2048, "instances": 3, "max_instances": 10,
    "last_heartbeat": "2026-09-24T17:59:50Z" } ]
```

### `GET /workers/{id}` — *admin*
Détail d'un worker. **`200`** / **`404`**.

### `POST /workers/register` — *token agent*
Un worker s'enregistre au démarrage (ou met à jour ses infos).

| Champ | Type |
|---|---|
| `hostname` | string (unique) |
| `ip` | string |
| `cpu` | int |
| `memory` | int (Mo) |
| `max_instances` | int |
| `agent_url` | string (URL interne de l'agent) |

- **`201`** : worker créé, `status = AVAILABLE`.
- **`200`** : worker déjà connu, mis à jour.
- **`401`** : token agent absent ou invalide.

### `POST /workers/heartbeat` — *token agent*
Signal de vie périodique (toutes les 10 s) + charge.

| Champ | Type |
|---|---|
| `hostname` | string |
| `cpu_load` | float |
| `memory_used` | int (Mo) |
| `containers` | int |

- **`200`** : `last_heartbeat` mis à jour ; un worker `OFFLINE` qui redonne signe repasse `AVAILABLE`.
- **`401`** : token invalide.

*(Côté Flask : un worker sans heartbeat depuis > 30 s passe `OFFLINE` — logique de S7.)*

### `GET /admin/monitoring` — *admin* — **(S10)**
Dashboard de supervision : instances actives, état + dernier heartbeat de chaque worker, santé
des services. **`200`** (HTML ou JSON selon l'implémentation retenue en S10).

---

## 7. API interne de l'agent (worker → Docker)

> Exposée **par chaque agent**, appelée **par Flask uniquement**, protégée par le token agent.
> Flask ne parle jamais directement au démon Docker.

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/containers` | Crée un conteneur : `image`, `ssh_port`, limites CPU/mémoire, labels `shellter.instance_id` et `shellter.expires_at`. Renvoie `container_id`, `ssh_port`. |
| `DELETE` | `/containers/{id}` | Détruit le conteneur. Idempotent (200 même s'il a déjà disparu). |
| `GET` | `/containers` | Liste les conteneurs portant le label `shellter`. |

---

## 8. Récapitulatif des routes

| # | Méthode | Route | Accès |
|---|---|---|---|
| 1 | GET | `/health` | public |
| 2 | GET/POST | `/register` | public |
| 3 | GET/POST | `/login` | public |
| 4 | POST | `/logout` | connecté |
| 5 | GET | `/dashboard` | connecté |
| 6 | GET | `/instances` | connecté |
| 7 | POST | `/rent` | connecté |
| 8 | POST | `/instances/{id}/stop` | propriétaire |
| 9 | GET | `/workers` | admin |
| 10 | GET | `/workers/{id}` | admin |
| 11 | POST | `/workers/register` | token agent |
| 12 | POST | `/workers/heartbeat` | token agent |
| 13 | GET | `/admin/monitoring` | admin (S10) |
