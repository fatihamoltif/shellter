# S10 — Déploiement en production & monitoring (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P4 / P2+P3
> **Output prof de la séance :** push Git → build → scan → déploiement → location en HTTPS.

---

## 1. Contexte et objectif

La S10 met le projet en « production » et le supervise. Ma partie (P4) : la **supervision**
(`/admin/monitoring`), le **smoke test** post-déploiement, et la procédure de **rollback**.

- P1 → registre privé + SBOM · P2 → `deploy.yml` depuis le pipeline · P3 → HTTPS · **P4 →
  supervision + smoke test + rollback**.

**Preuve attendue :** smoke test automatique, rollback simulé avec succès.

---

## 2. Ma partie P4 en détail

### 2.1 Supervision — `/admin/monitoring` (`app/monitoring.py`)
Endpoint (connecté) qui renvoie l'état du parc en JSON :
```json
{
  "services": { "flask": "up", "db": "up" },
  "instances": { "active": 3, "by_status": { "running": 3 } },
  "workers": [
    { "hostname": "worker1", "ip": "192.168.56.11", "status": "AVAILABLE",
      "last_heartbeat": "2026-10-04T12:...", "instances": 2 }
  ]
}
```
→ nombre d'**instances actives**, **état + dernier heartbeat** de chaque worker, **santé des
services**. (Restriction admin = raffinement à venir ; aujourd'hui `login_required`.)

### 2.2 Smoke test post-déploiement (`scripts/smoke_test.py`)
Vérifie en quelques secondes, **après un déploiement**, que l'essentiel répond :
`/health` → inscription + connexion → **location minimale** (`/rent`).
```bash
BASE_URL=https://shellter.local python scripts/smoke_test.py   # sortie 0 si OK, 1 sinon
```

### 2.3 Rollback (`scripts/rollback.sh`)
Chaque déploiement = un **tag** Git + une image taguée. En cas de problème, on **redéploie le tag
précédent**, puis on rejoue le smoke test :
```bash
scripts/rollback.sh v1.0        # checkout du tag -> redéploiement -> smoke test
```

---

## 3. Comment tester
```bash
# supervision + tous les tests unitaires (35)
python -m pytest -v

# smoke test contre la stack docker (lancée)
docker compose -f docker-compose.ci.yml up -d --build
BASE_URL=http://localhost:8080 python scripts/smoke_test.py
```

---

## 4. Preuve obtenue (confirmée en local)
- **Supervision** : `/admin/monitoring` renvoie services + instances + workers (2 tests verts).
- **Smoke test** : contre la vraie stack →
  ```
  OK  /health
  OK  inscription + connexion
  OK  location (/rent -> 201)
  [OK] SMOKE TEST REUSSI
  ```
- **Rollback simulé** : tag `v1.0` → « retour » sur `v1.0` → **smoke test post-rollback OK** → retour
  sur `alijamai`. Rollback **réussi**.
- **35 tests unitaires** + 3 d'intégration + sécurité → **CI verte**.

---

## 5. Ce qu'il reste pour le TEST FINAL (démo depuis zéro)
Le scénario complet de la prof (`vagrant destroy` → `up` → `site.yml` → déploiement par le pipeline
→ location en **HTTPS** → `docker kill` → `vagrant halt worker1` → expiration) nécessite aussi :
- le **registre privé + SBOM** (P1), le **`deploy.yml`** réel (P2), le **HTTPS/Nginx** (P3), et
  l'**agent réel** de P3.

Ma partie (supervision, smoke test, rollback) est prête et branchée : le smoke test se lance tel quel
après le déploiement réel, et le rollback rejoue n'importe quel tag.

> Tag de release posé : **`v1.0`** (fin S10). Tags prévus par le plan : `mvp-v1` (S6), `rc1` (S9), `v1.0` (S10).
