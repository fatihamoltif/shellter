# S6 — API Web : location (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P3 / P2+P4
> **Output prof de la séance :** un utilisateur loue une distro et obtient un accès SSH fonctionnel.

---

## 1. Contexte et objectif

La S6 est le **cœur métier** de Shellter : transformer une demande utilisateur en conteneur réel.
Ma partie (P4) est la plus centrale : le **Resource Manager** (décider *où* déployer) et l'**API de
location** (`/rent`, `/instances`, `/instances/<id>/stop`).

- P1 → images des distributions + SSH · P2 → Worker Agent (enregistrement) · P3 → Worker Agent
  (cycle de vie conteneurs) · **P4 → Resource Manager + `/rent`**.

**Preuve attendue :** deux locations en parallèle obtiennent des ports distincts, et la location
d'un autre utilisateur renvoie 404.

---

## 2. Ma partie P4 en détail

### 2.1 Le Resource Manager (`app/resource_manager.py`)
Décide **sur quel worker** créer l'instance. C'est de la logique pure (testable sans réseau).

**Règles de sélection (`select_worker`) :**
- **Éligible** = `status == AVAILABLE` **et** heartbeat < 30 s **et** capacité restante ;
- **Choisi** = le worker qui héberge le **moins d'instances actives** ;
- Statuts « actifs » (occupent un worker) : `pending, creating, running, recovering`.

**Autres fonctions :**
- `pick_free_ssh_port()` : un port libre dans `20000–30000` (non utilisé par une instance active) ;
- `worker_is_full()` : le worker passe **BUSY** s'il atteint `max_instances`.

### 2.2 L'API de location (`app/api.py`)

**`POST /rent`** — déroulé complet :
```
1. valide : utilisateur connecté, distribution enabled, durée ∈ {30, 60, 120}
2. Resource Manager -> choisit le worker le moins chargé
3. attribue un port SSH libre + génère des credentials (ssh_user/ssh_secret)
4. crée l'Instance (status=creating) et le Rental (status=ACTIVE)
5. appelle l'agent du worker -> crée le conteneur
6. succès -> Instance=running (+ worker BUSY si plein)
   échec  -> Instance=error, Rental=CANCELLED, HTTP 502
-> 201 { instance_id, rental_id, status, ssh_command, expires_at }
```

**Codes de retour :** `201` créée · `400` params invalides · `404` distro inconnue · `503` aucun
worker · `502` échec agent.

**`GET /instances`** — liste **uniquement** les instances de l'utilisateur courant.

**`POST /instances/<id>/stop`** — propriétaire only : détruit le conteneur (agent), passe l'instance
`stopped`, le rental `CANCELLED`, libère le worker (`BUSY → AVAILABLE` si plus plein). **404** si
l'instance n'appartient pas à l'utilisateur (on ne révèle pas son existence).

### 2.3 La couture vers l'agent (`app/agent_client.py`)
Flask ne parle **jamais** directement au démon Docker : il appelle l'**API de l'agent** du worker
(`POST {agent_url}/containers`). L'agent réel est la partie de P3. Ce module est la « couture » :
un client HTTP simple, **facilement mocké** dans les tests → on teste toute l'orchestration Flask
sans vrai conteneur.

---

## 3. Les tests (`tests/test_rent.py`) — 13 tests

| Groupe | Tests |
|---|---|
| **Resource Manager** | aucun worker → None ; heartbeat périmé ignoré ; choisit le moins chargé ; ignore un worker plein |
| **`/rent`** | login requis ; succès (201, ssh_command) ; durée invalide (400) ; distro inconnue (404) ; aucun worker (503) ; **deux locations → ports distincts** |
| **Contrôle d'accès** | **instance d'un autre → 404** ; stop de sa propre instance (conteneur supprimé, rental CANCELLED) ; `/instances` ne liste que les siennes |

---

## 4. Comment tester
```bash
pip install -r requirements-dev.txt
pytest -v          # 28 passed (13 location + 8 auth + 7 modèles)
```

### Essai manuel (curl), une fois l'infra prête
```bash
curl -X POST http://127.0.0.1:5000/rent \
     -H "Content-Type: application/json" -b cookies.txt \
     -d '{"distribution_id": 1, "duration_minutes": 30}'
# -> { "status": "running", "ssh_command": "ssh shellter@192.168.56.11 -p 20000", ... }
```
> L'API est **exemptée de CSRF** (JSON, appelée par curl/l'agent), contrairement aux formulaires web.

---

## 5. Preuve obtenue
- **Deux locations en parallèle → ports distincts** ✅
- **Instance d'un autre utilisateur → 404** ✅
- Bonus : worker absent → 503, durée invalide → 400, distro inconnue → 404, stop → rental CANCELLED.
- **CI verte** (28 tests).

---

## 6. Ce qu'il reste pour le TEST MVP #1 (fin de séance)
Le parcours réel *inscription → connexion → location Ubuntu → SSH → Alpine sur un autre worker →
stop* nécessite :
- l'**agent réel** de P3 (`POST /containers` qui lance vraiment le conteneur) ;
- les **images SSH** de P1 (Ubuntu/Debian/Alpine avec `openssh-server`) ;
- des **workers enregistrés** (P2, `POST /workers/register` + heartbeat).

Ma logique (Resource Manager + `/rent` + `/instances` + stop) est prête et branchée sur la couture
agent : dès que l'agent de P3 est là, on remplace le mock par l'appel réel **sans changer ma logique**.
