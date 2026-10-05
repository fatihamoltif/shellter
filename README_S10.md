# Séance 10 (S10) : Déploiement Continu Automatisé (CD)

L'objectif de cette séance est d'étendre notre pipeline d'Intégration Continue (CI) en y ajoutant le Déploiement Continu (CD). Le but final est qu'un code validé et scanné soit automatiquement déployé sur l'infrastructure de production sans aucune intervention manuelle.

## 1. Le Playbook de Déploiement (`ansible/deploy.yml`)

Un nouveau playbook Ansible a été conçu spécifiquement pour le cycle de livraison (Release) et diffère du playbook de configuration initiale de l'infrastructure. 

**Que fait-il ?**
- **Sur le Contrôleur (Nœud Principal) :** Il met à jour le fichier `.env` du projet pour spécifier explicitement le nouveau tag de l'image Docker (généré lors du build). Ensuite, il déclenche un `docker compose up -d` forçant le *pull* des images et la recréation des conteneurs obsolètes.
- **Sur les Workers (Agents) :** Il effectue un `docker pull` de la toute nouvelle image de l'agent Shellter, puis relance explicitement le conteneur `shellter-agent` avec les paramètres à jour.

Le tag de l'image (le SHA du commit ou la version Git) est injecté dynamiquement dans ce playbook grâce à la variable extra `-e "image_tag=xxx"`.

## 2. Le Pipeline GitHub Actions (Le Job `deploy`)

Le workflow principal `.github/workflows/docker-build.yml` a été étendu.

**Les modifications majeures :**
1. **Déclenchement Manuel :** Ajout de l'événement `workflow_dispatch` permettant de lancer (ou relancer) le pipeline et le déploiement depuis l'interface GitHub avec un bouton.
2. **Le Job `deploy` :** Ce job s'exécute uniquement si l'étape de construction (Build) et le Security Gate (Trivy) sont verts (`needs: build-and-test`).
3. **Le Processus de Déploiement :** 
   - La machine éphémère de GitHub Actions (runner) s'équipe d'Ansible.
   - Elle récupère la clé SSH de production, chiffrée de manière sécurisée dans les secrets GitHub (`SSH_PRIVATE_KEY`).
   - Elle détermine la version (tag) correspondant au commit.
   - Elle lance la commande `ansible-playbook` directement sur notre inventaire, mettant ainsi l'infrastructure cible dans la bonne version.

## 3. Sécurité des Secrets

Plutôt que d'exposer les identifiants en clair, l'approche DevSecOps a été maintenue en utilisant les `Repository Secrets` de GitHub :
- `SSH_PRIVATE_KEY` : Clé asymétrique pour garantir la connexion sécurisée du pipeline aux serveurs.
- `DEPLOY_USER` : L'utilisateur restreint qui exécute les mises à jour.
- `VAULT_PASSWORD` : Le secret permettant de déchiffrer les données sensibles de l'infrastructure Ansible à la volée.

**Résultat :** Un pipeline CI/CD de bout-en-bout, du `git push` au déploiement en production, totalement unifié et traçable !
