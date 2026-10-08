# Répartition du travail — branche `kubernetes`

Reprend la matrice de [`PLAN.md`](PLAN.md). Mapping proposé membre ⇄ rôle (à ajuster par
l'équipe) :

| Rôle (plan) | Membre | Thème |
|---|---|---|
| **P1** | **fatihamoltif** | cluster / infra / RBAC / images |
| **P2** | **YOUSSEF4315** | déploiement de la stack / client K8s |
| **P3** | **imenmezrigui-sketch** | cycle de vie des pods / expiration / scans |
| **P4** | **JamaiAli** | orchestration / résilience / doc / CI |

## Fichiers par membre

### P1 — fatihamoltif
- `ansible/k3s.yml`, `ansible/roles/k3s_server/**`
- `k8s/rbac.yaml`, `k8s/secret.example.yaml`, `k8s/configmap.yaml`
- (images SSH : réutilise `docker/ssh/Dockerfile` existant)

### P2 — YOUSSEF4315
- `ansible/roles/k3s_agent/**`
- `k8s/postgres-statefulset.yaml`, `k8s/postgres-service.yaml`
- `app/k8s_client.py`

### P3 — imenmezrigui-sketch
- `k8s/flask-deployment.yaml`, `k8s/flask-service.yaml`
- `k8s/expiration-cronjob.yaml`, `scripts/k8s_reaper.py`

### P4 — JamaiAli
- `k8s/ingress.yaml`, `k8s/env-deployment.template.yaml`
- `app/api.py` (adaptation `/rent` + `/stop` K8s), `app/reconciler.py`, `scripts/k8s_reconciler.py`
- `k8s/reconciler-cronjob.yaml`, `requirements.txt` (lib `kubernetes`)
- `.github/workflows/k8s-ci.yml`, `docs/kubernetes/**`

## Note sur la paternité git (important)

Cette branche a été **prototypée** par Ali (JamaiAli) : tous les commits initiaux sont donc
à son nom. Pour que l'historique reflète **honnêtement** la contribution de chacun sans
falsifier l'auteur, chaque membre reprend **sa** partie et la **commite lui-même** depuis sa
machine (patches fournis par Ali). Un commit = la personne qui l'a réellement fait.
