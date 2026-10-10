# Démo locale sur k3d (cluster k3s mono-nœud dans Docker)

Permet de **démontrer la version Kubernetes en vrai** sur une seule machine, quand un
cluster 4 nœuds sur VM n'est pas possible (RAM). Un seul nœud k3s tourne dans Docker.

## Pré-requis
- **Docker Desktop** démarré
- **kubectl** (fourni par Docker Desktop)
- **k3d** — `k3d-windows-amd64.exe` depuis https://github.com/k3d-io/k3d/releases
  (place-le p.ex. dans `%LOCALAPPDATA%\k3d\k3d.exe`)

## Mise en place (une commande)
Depuis la racine du dépôt, sur la branche `kubernetes` :
```powershell
.\k8s\local-k3d\setup.ps1
```
Ça : crée le cluster k3d → build+importe les images → déploie Postgres, Flask (2 répliques),
l'expiration. Puis, dans un terminal dédié :
```powershell
kubectl -n shellter port-forward svc/flask 8080:80
```
→ ouvre **http://localhost:8080** (compte **admin / admin123**).

## Accès SSH à une instance louée
Le NodePort n'est pas routé jusqu'à Windows sur k3d → on passe par un port-forward
(remplace `env-X` par le service vu dans `kubectl -n shellter get svc`) :
```powershell
kubectl -n shellter port-forward svc/env-X 2222:22
# autre terminal :
ssh shellter@localhost -p 2222
```

## Nettoyage
```powershell
& "$env:LOCALAPPDATA\k3d\k3d.exe" cluster delete shellter
```

> ⚠️ Différences avec les manifests de prod (`k8s/`) : images en tag `:local`
> (importées, pas de registre) et `FLASK_CONFIG=development` (cookie non-Secure car accès
> HTTP via port-forward, sans Ingress TLS).
