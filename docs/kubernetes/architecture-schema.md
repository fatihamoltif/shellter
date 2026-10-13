# Schéma d'architecture — branche Kubernetes

Vue simplifiée de l'architecture de Shellter sur Kubernetes. L'application Flask ne
lance plus les conteneurs elle-même : elle pilote l'**API Kubernetes**, qui crée un
Deployment + un Service NodePort pour **chaque location**.

```mermaid
flowchart TB
    User(["Utilisateur<br/>(navigateur)"])
    SSHUser(["Utilisateur<br/>(client SSH)"])

    subgraph Cluster["Cluster Kubernetes — namespace shellter"]
        direction TB

        API[["API Kubernetes<br/>scheduler + controllers"]]

        FlaskSvc["Service flask<br/>(ClusterIP)"]
        subgraph FlaskDep["Deployment flask — 2 répliques (HA)"]
            F1["Pod Flask"]
            F2["Pod Flask"]
        end

        PgSvc["Service postgres<br/>(headless)"]
        Pg[("StatefulSet postgres<br/>+ volume persistant (PVC)")]

        subgraph Envs["Environnements loués — un par location"]
            EDep["Deployment env-N<br/>Pod SSH (Ubuntu/Debian/...)"]
            ESvc["Service env-N<br/>(NodePort 22)"]
        end

        subgraph Cron["CronJobs — chaque minute"]
            Reaper["shellter-reaper<br/>détruit les locations expirées"]
            Recon["shellter-reconciler<br/>aligne la base sur le cluster"]
        end
    end

    User -->|HTTPS| FlaskSvc --> FlaskDep
    FlaskDep -->|SQL| PgSvc --> Pg
    FlaskDep -->|"crée / supprime<br/>(ServiceAccount + RBAC)"| API
    API -->|déploie & ordonnance| Envs
    SSHUser -->|SSH| ESvc --> EDep
    Reaper -->|delete_env| API
    Recon -->|list_envs| API
```

## Légende rapide
- **Deployment flask (2 répliques)** → haute disponibilité du plan de contrôle.
- **StatefulSet postgres + PVC** → données durables (survit au redémarrage du Pod).
- **env-N** (Deployment + Service NodePort) → une instance louée = un déploiement à part entière, créé à la volée via l'API.
- **ServiceAccount + RBAC** → Flask n'a le droit de gérer que les Deployments/Services du namespace `shellter`.
- **CronJobs** → `reaper` (expiration) et `reconciler` (cohérence base ↔ cluster), relancés chaque minute.

## Correspondance avec la version « maison » (branche `main`)
| Brique `main` | Équivalent Kubernetes |
|---|---|
| Worker Agent + Resource Manager | API Kubernetes + scheduler |
| Heartbeat + reprise sur panne codés | self-healing & reschedule natifs |
| Worker d'expiration en boucle | CronJob `shellter-reaper` |
| docker-compose | Deployment / StatefulSet / Service |
