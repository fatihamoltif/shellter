# Installation de Docker - Environnement S3

## Explication S3

Dans le cadre de notre projet Shellter et de nos travaux pour ce semestre S3, nous utilisons Docker pour créer et gérer de manière rapide, légère et isolée des environnements Linux pour nos utilisateurs. Il est essentiel que nous disposions d'une configuration identique sur l'ensemble de nos machines (Noah, Aziz, Isselmou et Youssef) afin de garantir la reproductibilité de nos déploiements et d'éviter les problèmes de compatibilité entre nos environnements de développement et nos Workers. Ce guide détaille l'installation standardisée et sécurisée requise.

## Prérequis

Avant de procéder à l'installation, assurez-vous de respecter les conditions suivantes :
- **Système d'exploitation** : Une distribution Linux basée sur Debian ou Ubuntu (les commandes sont prévues pour ces systèmes).
- **Privilèges d'administration** : Vous devez avoir accès aux droits d'administration (pouvoir exécuter des commandes avec `sudo`).
- **Paquets de base** : Disposer d'une connexion internet active et d'un système à jour.

## Nettoyage préalable

Pour éviter tout conflit lors de l'installation, il est impératif de désinstaller proprement les anciennes versions non officielles de Docker (`docker.io`, `docker-engine`, etc.).

Exécutez la commande suivante :

```bash
sudo apt-get remove -y docker docker-engine docker.io containerd runc
```
*(Note : Il est tout à fait normal que la commande vous indique que certains de ces paquets ne sont pas installés).*

## Installation pas à pas

### 1. Configuration du dépôt officiel

Mettez à jour votre index de paquets et installez les dépendances nécessaires pour permettre à `apt` d'utiliser un dépôt via HTTPS :

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
```

Ajoutez la clé GPG officielle de Docker :

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

Configurez ensuite le repository stable :

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 2. Installation des paquets nécessaires

Une fois le dépôt ajouté, mettez de nouveau à jour l'index des paquets et installez Docker CE, le CLI, containerd et Docker Compose :

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

## Configuration post-installation

Par défaut, l'utilisation de Docker nécessite les droits d'administration (`sudo`). Pour qu'un utilisateur standard puisse exécuter des commandes Docker (nécessaire pour nos scripts de déploiement et notre confort), il faut l'ajouter au groupe `docker`.

1. Créez le groupe `docker` (il est généralement créé par défaut lors de l'installation) :
   ```bash
   sudo groupadd docker
   ```

2. Ajoutez votre utilisateur au groupe `docker` :
   ```bash
   sudo usermod -aG docker $USER
   ```

3. Appliquez les modifications sans avoir à vous déconnecter en exécutant :
   ```bash
   newgrp docker
   ```

## Validation

Pour s'assurer que l'installation et les permissions fonctionnent correctement, lancez un conteneur de test (sans utiliser `sudo`) :

```bash
docker run hello-world
```

Si le message **"Hello from Docker!"** s'affiche, cela signifie que votre installation est propre, sécurisée et prête pour nos déploiements du S3 !
