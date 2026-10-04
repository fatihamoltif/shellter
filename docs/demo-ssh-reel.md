# Démo : louer un VRAI conteneur et s'y connecter en SSH

> Intégration d'un **Worker Agent réel** (SDK Docker) + des **images SSH** (Ubuntu/Debian/Alpine),
> pour que la location crée un **vrai conteneur Linux** accessible en SSH.
>
> Deux stacks coexistent :
> - `docker-compose.ci.yml` → agent **mock** (rapide, utilisé par la CI, pas de docker-in-docker).
> - `docker-compose.real.yml` → agent **réel** (lance de vrais conteneurs sur le Docker de l'hôte).

---

## 1. Lancer la stack réelle
```powershell
cd C:\Users\jamai\OneDrive\Desktop\shellter-push
docker compose -f docker-compose.real.yml up -d --build
```
- `db` : PostgreSQL
- `agent` : le Worker Agent réel (socket Docker monté → crée des conteneurs sur l'hôte)
- `web` : Flask (worker seedé pointant sur l'agent réel, host = `localhost`)

## 2. Louer une instance (récupère le port + le mot de passe)
```powershell
& "C:\Users\jamai\AppData\Local\Python\pythoncore-3.14-64\python.exe" demo_rent.py
```
Sortie :
```json
POST /rent -> 201
{
  "distribution": "ubuntu:24.04",
  "status": "running",
  "ssh_command": "ssh shellter@localhost -p 20000",
  "ssh_password": "IRgjfbhWvvtd7_uvJUWZtg",
  ...
}
```
> ⏳ La **1re location d'une distro** construit son image SSH (Ubuntu ~30 s, Debian/Alpine idem) →
> ça peut prendre un peu de temps. Les suivantes sont instantanées.

## 3. Se connecter en SSH (pour de vrai !)
```powershell
ssh shellter@localhost -p 20000
# -> mot de passe : la valeur "ssh_password" ci-dessus
# -> à la 1re connexion, répondre "yes" pour accepter la clé d'hôte
```
Tu es dans le conteneur :
```
shellter@env-1:~$ cat /etc/os-release
NAME="Ubuntu"  VERSION="24.04.5 LTS"
```

## 4. Nettoyer
```powershell
# arrêter la stack (db + agent + web)
docker compose -f docker-compose.real.yml down -v
# supprimer les conteneurs loués (créés par l'agent, hors compose)
docker rm -f $(docker ps -aq --filter "label=shellter.instance_id")
```

---

## Comment ça marche
```
/rent  ->  web (Flask)  ->  agent réel (SDK Docker)  ->  docker run <image SSH>
                                                           port 22 publié sur localhost:<port>
client  ->  ssh shellter@localhost -p <port>  ->  conteneur loué
```
- L'agent monte `/var/run/docker.sock` → il crée des conteneurs **frères** sur le Docker de l'hôte.
- L'image SSH (`docker/ssh/`) installe `openssh-server` ; l'entrypoint crée l'utilisateur à partir des
  variables fournies à chaque location (aucun mot de passe figé).
- Le worker seedé a `ip=localhost` → la commande SSH pointe sur l'hôte.

> Note d'intégration : l'**agent réel** relève du scope **P3** et les **images SSH** du scope **P1**.
> Cette implémentation permet la démo SSH réelle ; elle se réconciliera avec leurs versions sur `main`.
