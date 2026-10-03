# 📘 Documentation S8 : Pipeline CI/CD et Build des Images (Rôle P2)

Cette section détaille la mise en place de la pipeline d'intégration continue (CI) via **GitHub Actions**, responsable de la construction, du test (Smoke Test) et du balisage (Tagging) de l'ensemble des images Docker de l'infrastructure Shellter.

## 1. Création des Dockerfiles

Nous avons mis en place une série de 5 Dockerfiles distincts afin de garantir que chaque composant puisse être conteneurisé et distribué proprement.

### Les Images Systèmes (OS)
Nous avons créé trois images destinées à héberger les environnements utilisateurs. Chacune d'entre elles installe et configure un serveur **OpenSSH (`sshd`)** pour permettre la connexion à distance, et expose le port `22` :
- `docker/Dockerfile.ubuntu` (basé sur `ubuntu:22.04`)
- `docker/Dockerfile.debian` (basé sur `debian:12`)
- `docker/Dockerfile.alpine` (basé sur `alpine:3.18`)

*Note : Pour les besoins du projet, l'utilisateur `root` a été configuré avec le mot de passe `root:root` et l'option `PermitRootLogin yes`.*

### Les Images de l'Infrastructure
- **Flask (Contrôleur)** : Nous avons mis à jour le fichier `docker/Dockerfile` existant pour s'assurer que le port `5000` soit formellement exposé (`EXPOSE 5000`).
- **L'Agent (Worker)** : Création de `docker/Dockerfile.agent`. Il embarque un environnement `python:3.11-slim`, installe les dépendances requises (`requirements.txt`) et exécute le script `agent.py` avec le drapeau `-u` (unbuffered) pour garantir la remontée des logs en temps réel.

## 2. Le Pipeline GitHub Actions (CI)

Le fichier `.github/workflows/docker-build.yml` a été créé pour orchestrer la chaîne de build automatique à chaque `push` (ou `pull_request`) sur les branches principales, ainsi que lors de la création d'un tag Git.

### A. Stratégie de Matrice (Matrix)
Pour optimiser les temps de build et mutualiser le code du pipeline, nous utilisons la directive `strategy.matrix`. Le pipeline itère automatiquement sur les 5 images (`flask`, `agent`, `ubuntu`, `debian`, `alpine`) en exécutant les mêmes étapes en parallèle.

### B. Balisage Dynamique (Tagging)
Chaque image construite reçoit au minimum un tag unique pour garantir la traçabilité :
- **Le tag SHA** : Les 7 premiers caractères du commit Git (ex: `shellter/flask:a1b2c3d`).
- **Le tag de Release** : Si le commit est accompagné d'un tag Git (ex: `v1.0.0`), l'image recevra également ce tag conditionnellement.

### C. Tests de Validation (Smoke Tests)
Avant d'être considérée comme valide (statut de pipeline "Success"), chaque image est testée en direct de façon autonome. Les tests implémentés sont synchrones et sans délais arbitraires (pas de `sleep`) :
- **Pour les OS (Ubuntu, Debian, Alpine)** : Un conteneur démarre et expose son port. L'utilitaire réseau `nc` (Netcat) interroge le port pour s'assurer que le service OpenSSH accepte bien les connexions.
- **Pour l'Agent** : Un conteneur éphémère exécute une ligne Python (`import docker`) pour garantir que toutes les dépendances requises ont bien été packagées dans l'image lors du build.
- **Pour Flask** : Un script Python éphémère initie la Factory Pattern de l'application Flask (`create_app('testing')`). Cela permet de valider instantanément qu'il n'y a pas d'erreur de syntaxe, que tous les modules (comme la base de données ou les routes) s'importent correctement, et que l'image est saine pour la production.

Grâce à ce système, toute anomalie bloquera la CI, protégeant ainsi l'infrastructure.
