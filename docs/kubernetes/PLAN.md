# Plan détaillé — Branche Kubernetes (Option B : version fonctionnelle)

> Objectif : réimplémenter l'orchestration de Shellter avec **Kubernetes** (distribution **k3s**,
> légère), en réutilisant les **4 VM Vagrant existantes** comme nœuds du cluster. On remplace le
> Worker Agent + Resource Manager + reprise sur panne par les mécanismes **natifs** de Kubernetes.
>
> ⚠️ C'est l'option **ambitieuse** : ~5 séances **+ beaucoup de travail perso** (courbe K8s raide),
> soit ~2-3 semaines calendaires à 4. Le point dur est la séance **K3**.

---

## 0. Architecture cible

```
                 Internet / client
                        │ HTTPS 443
                 ┌──────▼───────────────── cluster k3s ──────────────────┐
                 │  Ingress (Traefik, TLS)                                │
                 │        │                                               │
                 │   Service Flask ──► Deployment Flask (2 replicas)      │
                 │        │                     │ (ServiceAccount + RBAC) │
                 │   Service PostgreSQL ──► StatefulSet PostgreSQL + PVC  │
                 │                              │ appelle l'API K8s       │
                 │   ┌──────────── par location : ────────────┐          │
                 │   │  Pod "env-<id>" (image SSH) + Service    │          │
                 │   │  NodePort 30000-32767 -> port 22         │          │
                 │   └──────────────────────────────────────────┘         │
                 └────────────────────────────────────────────────────────┘
   nœuds : controller (k3s server) + worker1/2/3 (k3s agents)  = VM Vagrant
   client ──► ssh user@<node-ip> -p <nodeport> ──► Pod loué
```

### Correspondance « Shellter maison → Kubernetes »
| Brique maison (séances S1–S7) | Équivalent Kubernetes |
|---|---|
| Worker Agent (`agent_client`) | l'**API Kubernetes** (`kubernetes` python) |
| Resource Manager (`select_worker`) | le **scheduler** K8s (ou `nodeSelector`) |
| Heartbeat + statut worker | les **nœuds** + `kubelet` + health checks |
| `/rent` → créer un conteneur | créer un **Pod** (+ Service NodePort pour le SSH) |
| Reprise sur panne (S7) | **re-scheduling** natif (Deployment/ReplicaSet) |
| Expiration (`end_time`) | `Job activeDeadlineSeconds` ou **CronJob** de nettoyage |
| docker-compose du controller | manifests **Deployment / StatefulSet / Service / Ingress** |

### Prérequis & outils
- Les 4 VM Vagrant up (`192.168.56.10–13`).
- `k3s` (installé via Ansible), `kubectl` sur le poste, lib Python `kubernetes`.
- Un **registre d'images** (GitHub Container Registry, ou registre local k3s).
- `kubeconform` / `kube-score` (lint manifests), `Trivy` (scan images).

### Répartition « fil rouge » (continuité avec vos parties actuelles)
| | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| Thème | cluster / infra | déploiement de la stack | cycle de vie des pods (ex-agent) | orchestration / résilience / CI |

---

## K1 — Cadrage & montage du cluster k3s
**Binômes : P1+P2 / P3+P4** · **Output : `kubectl get nodes` → 4 nœuds `Ready`**

### P1 — k3s server sur le controller
- Nouveau rôle Ansible `k3s_server` :
  ```bash
  curl -sfL https://get.k3s.io | sh -s - server \
    --node-ip 192.168.56.10 --tls-san 192.168.56.10 --write-kubeconfig-mode 644
  ```
- Récupérer le **token** : `/var/lib/rancher/k3s/server/node-token`.
- Récupérer le **kubeconfig** : `/etc/rancher/k3s/k3s.yaml` (y remplacer `127.0.0.1` par `192.168.56.10`).
- **Preuve :** `kubectl get nodes` montre le controller `Ready`.

### P2 — Agents k3s sur les 3 workers
- Rôle Ansible `k3s_agent` (variable `k3s_token` depuis le controller) :
  ```bash
  curl -sfL https://get.k3s.io | K3S_URL=https://192.168.56.10:6443 \
    K3S_TOKEN=<token> sh -s - agent --node-ip 192.168.56.1X
  ```
- **Preuve :** les 3 workers rejoignent → `kubectl get nodes` = **4 `Ready`**.

### P3 — Accès cluster + pod de test
- Copier `k3s.yaml` dans `~/.kube/config` (poste / WSL), tester :
  ```bash
  kubectl get nodes
  kubectl run nginx --image=nginx && kubectl get pods && kubectl delete pod nginx
  ```
- **Preuve :** le pod nginx passe `Running`.

### P4 — Cadrage K8s
- `docs/kubernetes/architecture.md` : schéma (mermaid), **tableau de mapping** ci-dessus, liste exhaustive des manifests à produire, **stratégie de test** (kubeconform sur tous les manifests, smoke tests HTTP/SSH).
- **Preuve :** doc relue et validée par les 4.

**Test de fin de séance :** une personne qui n'a pas monté le cluster rejoue `kubectl get nodes` (4 Ready) et déploie/supprime un pod.
**Notions :** Kubernetes, k3s, nœuds, kubeconfig, token, Ansible.

---

## K2 — Déploiement de la stack (Flask + PostgreSQL)
**Binômes : P1+P3 / P2+P4** · **Output : Flask + PostgreSQL tournent sur le cluster**

### P1 — Secrets & configuration
- `Secret` `shellter-secrets` (SECRET_KEY, mot de passe DB) + `ConfigMap` (DATABASE_URL, variables non secrètes).
  ```bash
  kubectl create secret generic shellter-secrets \
    --from-literal=SECRET_KEY=... --from-literal=DB_PASSWORD=...
  ```
- Migrer les valeurs du **Vault Ansible** → Secret Kubernetes.
- **Preuve :** un pod de test voit bien les variables (`kubectl exec ... env | grep SECRET`).

### P2 — PostgreSQL persistant
- `postgres-statefulset.yaml` : image `postgres:16`, `volumeClaimTemplates` (PVC, storageClass `local-path` de k3s), `Service` headless, variables depuis le Secret.
- **Preuve :** `kubectl exec` → `psql -l` montre la base ; la donnée **survit à la suppression du pod** (PVC).

### P3 — Image & Deployment Flask
- Construire l'image Flask, la **pousser dans le registre**.
- `flask-deployment.yaml` : `Deployment` (2 replicas), `Service` ClusterIP, env depuis Secret/ConfigMap, **probes** `readiness`/`liveness` sur `/health`.
- **Preuve :** `kubectl get pods` → 2/2 `Running` ; `kubectl port-forward` + `curl /health` → 200.

### P4 — Ingress + HTTPS + smoke test
- `Ingress` (Traefik, intégré à k3s) vers le Service Flask + **TLS** (certificat auto-signé ou `cert-manager`).
- `shellter.local` dans `/etc/hosts` → `curl -k https://shellter.local/health`.
- **Preuve :** `/health` → 200 **en HTTPS** depuis l'extérieur du cluster.

**Test de fin de séance :** `kubectl delete pod <flask>` → recréé par le Deployment → `/health` toujours OK (rejoué par un non-auteur).
**Notions :** Deployment, StatefulSet, PVC, Service, Secret/ConfigMap, Ingress, probes, TLS.

---

## K3 — La location = un Pod par instance (le cœur) ⭐
**Binômes : P1+P4 / P2+P3** · **Output : `POST /rent` crée un vrai Pod SSH via l'API Kubernetes**

### P1 — Images SSH + droits (RBAC)
- Dockerfiles Ubuntu 24.04 / Debian 13 / Alpine avec `openssh-server` + entrypoint créant l'utilisateur SSH depuis des variables (pas de mot de passe figé) ; pousser au registre.
- `ServiceAccount` `shellter-api` + `Role` (verbes `create/delete/get/list` sur `pods` et `services`) + `RoleBinding`, monté dans le Deployment Flask.
- **Preuve :** `kubectl auth can-i create pods --as=system:serviceaccount:default:shellter-api` → `yes`.

### P2 — Client Kubernetes (remplace `agent_client`)
- `app/k8s_client.py` avec la lib Python `kubernetes` (`config.load_incluster_config()`) :
  `create_env(image, instance_id, ssh_user, ssh_secret)` → crée un **Pod** + un **Service NodePort** (port 22) ; `delete_env(instance_id)`.
- **Preuve :** appeler `create_env` → `kubectl get pods,svc` montre le Pod loué + son Service NodePort.

### P3 — Cycle de vie des pods
- `labels` (`shellter.instance_id`, `shellter.expires_at`), suppression Pod+Service, `list_envs()`, gestion d'échec (pas de Pod orphelin), nettoyage à mi-chemin.
- **Preuve :** 10 créations/suppressions successives **sans orphelin** (`kubectl get pods,svc`).

### P4 — `/rent` + Resource Manager version K8s
- Adapter `POST /rent` : au lieu du Worker Agent, appeler `k8s_client`. **Le scheduling est délégué à Kubernetes** (ou `nodeSelector` si on veut imposer un nœud). Stocker `pod_name`, `nodeport`, `node_ip` ; afficher `ssh user@<node-ip> -p <nodeport>`.
- Adapter `GET /instances` et `POST /instances/<id>/stop` → `delete_env`.
- **Preuve :** `POST /rent` → Pod `Running` → `ssh user@<node-ip> -p <nodeport>` **fonctionne** ; `stop` → Pod+Service supprimés.

**Test de fin de séance :** TEST MVP K8s #1 — login → `/rent` Ubuntu → SSH → `/rent` Alpine → `stop` (rejoué par un non-auteur).
**Notions :** API Kubernetes, RBAC, ServiceAccount, Pod, NodePort, scheduling.

---

## K4 — Résilience native + expiration
**Binômes : P1+P2 / P3+P4** · **Output : self-healing démontré (l'équivalent natif de ta S7)**

> **Décision de conception :** un `Pod` nu **n'est pas** reprogrammé si son nœud tombe. Pour avoir la
> résilience, on encapsule chaque location dans un **`Deployment` (1 replica)** (ou un `Job`), que
> Kubernetes recrée automatiquement.

### P1 — Auto-réparation du pod
- Convertir « Pod par location » → **Deployment par location** (1 replica).
- Démontrer : `kubectl delete pod <env>` → **recréé automatiquement**.
- **Preuve :** le Pod revient en < 30 s (nouveau nom).

### P2 — Panne de nœud
- `kubectl cordon` + `drain` d'un nœud, ou `vagrant halt worker1`.
- **Preuve :** les pods du nœud tombé sont **reschedulés** sur un autre nœud.

### P3 — Expiration automatique
- TTL : `Job` avec `activeDeadlineSeconds`, **ou** un **CronJob** de nettoyage qui supprime les
  Deployments/Services dont le label `shellter.expires_at` est dépassé, puis met la base à jour.
- **Preuve :** location de 2 min → env supprimé à l'échéance, base cohérente.

### P4 — Cohérence base ↔ cluster
- Réconciliateur : lister les pods/deployments, comparer avec la table `instances`, mettre à jour les
  statuts (`recovering`/`running`) et le **nouveau `node-ip`/`nodeport`** dans le dashboard quand un
  pod a migré.
- **Preuve :** après reschedule, le dashboard affiche le nouveau host/port.

**Test de fin de séance :** `delete pod` + `vagrant halt worker1` + expiration courte, rejoués par un non-auteur.
**Notions :** self-healing, Deployment/ReplicaSet, reschedule, Job/CronJob, réconciliation d'état.

---

## K5 — CI/CD + démo + documentation
**Binômes : P1+P3 / P2+P4** · **Output : `git push` → build → scan → déploiement sur le cluster**

### P1 — Build & push des images
- Pipeline : construire **Flask + les 3 images distro**, taguées par SHA de commit, poussées au registre.
- **Preuve :** les images du commit X sont dans le registre.

### P2 — Déploiement continu
- Depuis le pipeline : `kubectl apply -f manifests/` (ou **Helm**), avec le kubeconfig stocké en **secret CI**. Possibilité de passer par Ansible.
- **Preuve :** un `git push` sur `main` déclenche le déploiement ; la version déployée = le commit.

### P3 — Sécurité
- **Trivy** sur les images (gate CVE CRITICAL), **kubeconform**/**kube-score** sur les manifests.
- **Preuve :** une image vulnérable est bloquée ; un manifest non conforme est signalé.

### P4 — Documentation & démo
- `README-kubernetes.md` : le **mapping archi → K8s**, comment déployer, comment démontrer.
- Scénario de démo + répétition de soutenance.
- **Preuve :** démo rejouée de bout en bout, chacun sait expliquer une couche qu'il n'a pas écrite.

**Test de fin de séance :** TEST FINAL K8s — **depuis zéro** : `vagrant up` → Ansible installe k3s → pipeline déploie → location en HTTPS → SSH → self-healing démontré.
**Notions :** CI/CD, registre d'images, déploiement Kubernetes, sécurité images/manifests.

---

## Matrice obligatoire (chacun touche chaque notion)
| Notion | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| Cluster k3s / nœuds | server (K1) | agents (K1) | kubectl (K1) | cadrage (K1) |
| Manifests (Deploy/StatefulSet/Service) | Secrets (K2) | PostgreSQL (K2) | Flask (K2) | Ingress (K2) |
| API Kubernetes / RBAC | RBAC (K3) | client K8s (K3) | cycle de vie (K3) | /rent (K3) |
| Résilience | self-heal (K4) | panne nœud (K4) | expiration (K4) | cohérence (K4) |
| CI/CD & sécurité | build (K5) | deploy (K5) | scans (K5) | doc/démo (K5) |

---

## Risques & points durs
1. **K3 est le vrai défi** : faire parler Flask à l'API K8s + exposer le SSH par NodePort. Prévoir du temps.
2. **Exposition SSH** : NodePort limite la plage à `30000–32767` ; mapper proprement et éviter les collisions.
3. **Résilience** : une location doit être un **Deployment/Job**, pas un Pod nu, sinon pas de reschedule.
4. **Registre d'images** : à décider tôt (GHCR vs registre local) — bloquant pour K2/K3/K5.
5. **Courbe d'apprentissage** : si personne ne connaît K8s, **chaque estimation double**.

## Checklist finale (avant soutenance)
- [ ] `kubectl get nodes` → 4 Ready, recréables par Ansible depuis zéro.
- [ ] Flask + PostgreSQL déployés, `/health` en HTTPS.
- [ ] `POST /rent` crée un Pod SSH joignable ; `stop` le supprime.
- [ ] `kubectl delete pod` → recréé ; `halt` d'un nœud → reschedule.
- [ ] Expiration automatique fonctionnelle.
- [ ] Pipeline : push → build → scan → déploiement sur le cluster.
- [ ] `README-kubernetes.md` + démo répétée ; chacun explique une couche qu'il n'a pas écrite.
