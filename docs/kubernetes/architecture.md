# Architecture Kubernetes — Shellter (branche `kubernetes`)

> Cadrage (séance K1, partie P4). Réimplémentation de l'orchestration de Shellter avec
> **k3s**, en réutilisant les 4 VM Vagrant comme nœuds du cluster. Les briques « maison »
> (Worker Agent, Resource Manager, reprise sur panne) sont remplacées par les mécanismes
> **natifs** de Kubernetes.

## Vue d'ensemble

```mermaid
flowchart TB
  U[Client] -->|HTTPS 443| ING[Ingress Traefik + TLS]
  ING --> SVC[Service flask]
  SVC --> DEP[Deployment flask x2]
  DEP -->|ServiceAccount + RBAC| API[(API Kubernetes)]
  DEP --> PG[(Service postgres)]
  PG --> STS[StatefulSet postgres + PVC]
  API -->|par location| ENV[Deployment env-ID 1 pod + Service NodePort]
  U -->|ssh user@node-ip -p nodeport| ENV
  subgraph CLUSTER["cluster k3s = 4 VM Vagrant"]
    ING
    SVC
    DEP
    PG
    STS
    ENV
  end
```

- **controller** (`192.168.56.10`) : nœud **k3s server**.
- **worker1/2/3** (`.11/.12/.13`) : nœuds **k3s agents**.
- Une **location** = un **Deployment (1 replica)** + un **Service NodePort** exposant le port 22.

## Correspondance « Shellter maison → Kubernetes »

| Brique maison (main) | Équivalent Kubernetes (cette branche) |
|---|---|
| Worker Agent (`agent_client`) | l'**API Kubernetes** (`app/k8s_client.py`) |
| Resource Manager (`select_worker`) | le **scheduler** k3s |
| Heartbeat + statut worker | les **nœuds** + `kubelet` + probes |
| `/rent` → créer un conteneur | créer un **Deployment** + **Service NodePort** |
| Reprise sur panne (S7) | **re-scheduling natif** (Deployment/ReplicaSet) |
| Expiration (`end_time`) | **CronJob** de nettoyage (`k8s_reaper.py`) |
| `docker-compose` du controller | manifests **Deployment / StatefulSet / Service / Ingress** |
| Chiffrement SSH, quota, admin, migrations | **inchangés** (réutilisés tels quels) |

## Manifests produits (`k8s/`)

| Fichier | Rôle | Partie |
|---|---|---|
| `00-namespace.yaml` | namespace `shellter` | — |
| `rbac.yaml` | ServiceAccount + Role + RoleBinding | P1 |
| `secret.example.yaml` / `configmap.yaml` | secrets & config | P1 |
| `postgres-statefulset.yaml` / `postgres-service.yaml` | base persistante | P2 |
| `flask-deployment.yaml` / `flask-service.yaml` | control plane | P3 |
| `ingress.yaml` | HTTPS (Traefik + TLS) | P4 |
| `env-deployment.template.yaml` | gabarit d'une location (généré par `k8s_client`) | P1/P4 |
| `expiration-cronjob.yaml` | expiration automatique | P3 |
| `reconciler-cronjob.yaml` | réconciliation base ↔ cluster | P4 |

## Choix de conception
- Une **location = un Deployment (1 replica)**, pas un Pod nu → si le pod ou son nœud
  tombe, Kubernetes le recrée (self-healing natif, équivalent de la reprise sur panne S7).
- La date d'expiration est stockée en **annotation** `shellter.expires_at`, **pas en label** :
  les valeurs de label K8s interdisent `:` et `+`, présents dans les dates ISO.
- Les images sont publiées au registre par la CI (`ghcr.io/<owner>/shellter-*`) ; un
  **imagePullSecret** est nécessaire côté cluster si le package est privé.

## Stratégie de test

**Vérifié aujourd'hui — sans cluster, CI verte :**
- `kubeconform` sur tous les manifests (lint des schémas Kubernetes).
- Build + push des images (Flask + 3 distros SSH) et scan **Trivy** (gate CRITICAL).
- Tests unitaires de l'application : `pytest -q` → **55 tests**.

**Sur un cluster — procédure (voir [`README-kubernetes.md`](README-kubernetes.md)) :**
- **Composant** : `kubectl get nodes` (4 Ready) ; PVC qui survit à la suppression du pod Postgres.
- **E2E** : `/health` en HTTPS via l'Ingress ; `POST /rent` → `ssh user@<node-ip> -p <nodeport>`.
- **Résilience** : `kubectl delete pod env-<id>` → recréé ; `vagrant halt worker1` → reschedule.
- **Expiration** : location courte → CronJob supprime l'env, base cohérente.

> Le déploiement sur cluster réel n'a pas été réalisé sur le matériel de dev (contraintes
> RAM) ; voir la note d'état dans [`README-kubernetes.md`](README-kubernetes.md).
