# Séance 9 (S9) : DevSecOps & Pipeline CI/CD

Ce document retrace les actions effectuées lors de la Séance 9, dont l'objectif était d'intégrer des pratiques de sécurité (Hardening) et des contrôles automatisés (Security Gate) dans notre chaîne d'intégration continue (CI/CD) sur GitHub Actions.

## 1. Hardening des Images Docker (Réduction de surface)

Afin de réduire les vulnérabilités et de respecter les bonnes pratiques DevSecOps, les 5 images de l'infrastructure (Flask, Agent, Ubuntu, Debian, Alpine) ont été optimisées (Hardening). 

Les principes suivants ont été appliqués :
* **Images minimales :** Remplacement des images de base lourdes par des versions "slim" ou "alpine" (ex: utilisation de `debian:12-slim` pour Debian).
* **Nettoyage des caches :** Ajout de commandes comme `--no-cache-dir` pour pip ou `rm -rf /var/lib/apt/lists/*` pour apt afin de limiter la taille et la surface d'attaque.
* **Principe du moindre privilège (Utilisateurs non-root) :** 
  * Création et utilisation des utilisateurs `appuser` (Flask) et `agentuser` (Agent).
  * Pour les serveurs (Debian, Ubuntu, Alpine), bien que le daemon `sshd` doive être lancé en root, un utilisateur standard `ansible` a été configuré pour les connexions.
* **Absence de secrets en dur :** Suppression des mots de passe en clair (`root:root`) initialement écrits dans les Dockerfiles. Les accès SSH ont été durcis en interdisant le login root (`PermitRootLogin no`).

## 2. Mise en place d'un Security Gate (Trivy)

Une étape d'analyse de vulnérabilités a été insérée dans le pipeline `.github/workflows/docker-build.yml` via l'outil open-source **Trivy**.

**Configuration du Gate :**
Le scan se lance juste après la phase de *build*. Il agit comme une véritable "barrière" :
- Analyse des vulnérabilités de l'OS et des bibliothèques (`vuln-type: 'os,library'`).
- **Blocage critique** : Le paramètre `exit-code: 1` est configuré exclusivement pour le niveau `severity: 'CRITICAL'`.
- Si une vulnérabilité critique est découverte, le pipeline échoue immédiatement et empêche l'exécution du "Smoke test" ou de tout futur déploiement.

## 3. Preuve de fonctionnement (Test du Pipeline)

Pour prouver l'efficacité du Security Gate, un test en deux temps a été exécuté sur la branche `yousseframmeh` :

1. **Le test d'échec (Vulnerability Injection) :**
   - Le `Dockerfile.debian` a été volontairement altéré en utilisant une très vieille image vulnérable (`FROM debian:10`).
   - *Résultat CI :* Le pipeline a **échoué** (croix rouge) au niveau du scan Trivy, bloquant la suite du processus en raison de la présence de nombreuses CVE "CRITICAL".
   
2. **Le correctif (Remédiation) :**
   - Le `Dockerfile.debian` a été corrigé pour repasser sur l'image sécurisée (`FROM debian:12-slim`).
   - *Résultat CI :* Le pipeline est **passé avec succès** (vert), prouvant que l'image modifiée est saine.

Les traces de ces exécutions sont directement consultables dans l'onglet **Actions** de GitHub sur les commits correspondants.
