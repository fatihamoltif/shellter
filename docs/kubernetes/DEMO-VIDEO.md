# Script de démo/présentation — branche Kubernetes

Guide à suivre pendant l'enregistrement ou la soutenance. Chaque étape :
**💻 commande** · **🎙️ phrase à dire** · **👁️ ce qu'on voit**.

> **Setup caméra conseillé** : navigateur (gauche) + 2 terminaux PowerShell (droite).
> Terminal **A** = commandes · Terminal **B** = réservé aux `port-forward`.
> Accès dashboard : **http://localhost:8080** · comptes : **admin / admin123**, **demo / password123**.

---

## 0. Préparation (AVANT de filmer)
```powershell
cd C:\Users\jamai\OneDrive\Desktop\shellter-push
git checkout kubernetes ; git pull
kubectl -n shellter delete deploy,svc -l app=shellter-env   # nettoie d'anciennes instances
.\k8s\local-k3d\setup.ps1                                   # cluster + build + deploy (2-5 min)
kubectl -n shellter get deploy,pods                          # attendu : flask 2/2, postgres 1/1
```
Terminal **B** (laisser tourner tout le long) :
```powershell
kubectl -n shellter port-forward svc/flask 8080:80
```
Ouvrir **http://localhost:8080** → page de login. **Prêt.**

---

## 1. Introduction & le cluster

🎙️ *« Shellter est une plateforme de location d'environnements Linux accessibles en SSH. Voici la version réimplémentée avec Kubernetes : on a remplacé notre orchestration "maison" par un vrai orchestrateur. »*

💻 (terminal A)
```powershell
kubectl get nodes
```
👁️ nœud `Ready` · 🎙️ *« Voici notre cluster Kubernetes (k3s). »*

💻
```powershell
kubectl -n shellter get deploy,svc
```
👁️ `flask` (2 répliques), `postgres` · 🎙️ *« L'application Flask et la base PostgreSQL tournent comme des Pods, exactement comme en production. »*

---

## 2. Démo normale (parcours utilisateur)

🎙️ *« Côté utilisateur, l'interface est identique à notre version classique. »*

**Connexion** (navigateur) : `admin` / `admin123`.

**Louer** : Distribution **Ubuntu 24.04**, Durée **30 min**, clic **Louer**.
👁️ une instance apparaît (commande SSH + mot de passe) · 🎙️ *« Je loue un environnement Ubuntu. En coulisses, l'application appelle directement l'API Kubernetes. »*

**Prouver que c'est un vrai Pod** 💻 :
```powershell
kubectl -n shellter get deploy,pods,svc
```
👁️ un `env-X` (Deployment + Pod + Service NodePort) · 🎙️ *« Le clic "Louer" a créé un vrai Deployment et un Service NodePort. Chaque location est un déploiement Kubernetes à part entière. »*

**SSH dans l'instance** — repère le nom `env-X` (colonne du `get svc`). Terminal **B** :
```powershell
kubectl -n shellter port-forward svc/env-X 2222:22
```
Terminal **A** :
```powershell
ssh shellter@localhost -p 2222
# (coller le mot de passe affiché dans le dashboard)
hostname
cat /etc/os-release
exit
```
🎙️ *« Je me connecte en SSH : on est bien dans le conteneur Linux, à l'intérieur d'un Pod Kubernetes, loué depuis le dashboard. »*

**Prolonger** (navigateur) : `+30 min` → **Prolonger**.
🎙️ *« On peut prolonger une location en cours. »*

**Admin** : **Gérer les distributions** puis **Monitoring**.
🎙️ *« En tant qu'admin, je gère les distributions proposées et je supervise le système. »*

**Arrêter** : bouton **Arrêter**, puis 💻 :
```powershell
kubectl -n shellter get deploy,svc
```
👁️ l'`env-X` a disparu · 🎙️ *« L'arrêt supprime le déploiement et son service du cluster, via l'API Kubernetes. »*

---

## 3. Scénarios critiques

> Avant chaque scénario, assure-toi d'avoir **une instance active** (refais **Louer** si besoin).

### A. ⭐ Un conteneur loué plante (auto-guérison)
🎙️ *« Premier cas critique : que se passe-t-il si le conteneur d'un utilisateur plante ? »*
💻
```powershell
kubectl -n shellter get pods -l app=shellter-env
kubectl -n shellter delete pod -l app=shellter-env
kubectl -n shellter get pods -l app=shellter-env -w
```
👁️ un **nouveau** Pod `env-X-...` réapparaît en quelques secondes (`Ctrl+C` pour sortir)
🎙️ *« Je tue le conteneur. Kubernetes le détecte et le recrée tout seul — c'est le self-healing natif, l'équivalent de notre reprise sur panne, mais sans une ligne de code de notre part. »*

### B. ⭐ Le plan de contrôle (Flask) plante (haute disponibilité)
🎙️ *« Deuxième cas : et si c'est notre application elle-même qui plante ? »*
💻
```powershell
kubectl -n shellter get pods -l app=flask
$p = kubectl -n shellter get pod -l app=flask -o jsonpath="{.items[0].metadata.name}"
kubectl -n shellter delete pod $p
```
👁️ (navigateur) **rafraîchir le dashboard** → il répond toujours
🎙️ *« Je tue une des deux répliques. Le dashboard reste disponible : la seconde prend le relais, aucune coupure. »*
💻
```powershell
kubectl -n shellter get pods -l app=flask
```
👁️ de nouveau **2/2** · 🎙️ *« Et Kubernetes recrée la réplique manquante. Haute disponibilité par conception. »*

### C. ⭐ Expiration automatique
🎙️ *« Troisième cas : la gestion automatique de la fin de vie des locations. »*
(loue une instance, puis)
💻
```powershell
kubectl -n shellter exec deploy/flask -- python scripts/backdate_demo.py
```
🎙️ *« Pour la démo, j'avance la date de fin dans le passé au lieu d'attendre 30 minutes. »*
(attendre ~1 min)
💻
```powershell
kubectl -n shellter get deploy,svc
kubectl -n shellter get jobs
```
👁️ l'`env-X` a disparu ; un Job `shellter-reaper-...` est `Completed`
🎙️ *« Un CronJob s'exécute chaque minute et détruit automatiquement les environnements expirés. »*

### D. ⭐ (Avancé) Panne d'une machine entière
> Nécessite un cluster **multi-nœuds**. À faire **avant** ce scénario (hors caméra) :
> ```powershell
> & "$env:LOCALAPPDATA\k3d\k3d.exe" cluster delete shellter
> & "$env:LOCALAPPDATA\k3d\k3d.exe" cluster create shellter --servers 1 --agents 2 --wait
> .\k8s\local-k3d\setup.ps1
> ```
(loue 2-3 instances, puis)
💻
```powershell
kubectl get nodes
kubectl -n shellter get pods -o wide        # noter le nœud des env
docker stop k3d-shellter-agent-0            # "débrancher" une machine
kubectl get nodes                           # le nœud passe NotReady
kubectl -n shellter get pods -o wide -w     # les Pods sont reschedulés ailleurs
```
👁️ les Pods du nœud coupé réapparaissent sur un autre nœud (`Ctrl+C`)
🎙️ *« La machine tombe, Kubernetes la marque indisponible et replace ses Pods sur un nœud sain. L'utilisateur ne perd pas son environnement. »*
(remettre le nœud : `docker start k3d-shellter-agent-0`)

---

## 4. Conclusion
🎙️ *« Pour résumer : le produit est identique à notre version maison, mais toute l'orchestration est confiée à Kubernetes. »*

| Brique maison (`main`) | Équivalent Kubernetes |
|---|---|
| Worker Agent + Resource Manager | API Kubernetes + scheduler |
| Heartbeat + reprise sur panne codés main | self-healing & reschedule **natifs** |
| docker-compose | Deployment / StatefulSet / Service / Ingress |

🎙️ *« On a prouvé qu'on sait réimplémenter un orchestrateur à la main — et qu'on sait aussi s'appuyer sur l'outil standard de l'industrie, qui gère plus de pannes, nativement. »*

---

## 5. Nettoyage (après)
```powershell
& "$env:LOCALAPPDATA\k3d\k3d.exe" cluster delete shellter
```

---
### Antisèche
- Dashboard : http://localhost:8080 (admin / admin123)
- Nom d'une instance : `kubectl -n shellter get svc` → `env-X`
- SSH : `kubectl -n shellter port-forward svc/env-X 2222:22` puis `ssh shellter@localhost -p 2222`
- Tout voir : `kubectl -n shellter get deploy,pods,svc,jobs`
