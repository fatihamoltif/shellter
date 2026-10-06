# S11 — Consolidation sur `main` & fonctionnalités avancées

> Après les séances S1→S10 (travail P4 sur `alijamai`), cette étape consolide le projet sur la
> branche **`main`** : intégration du travail des coéquipiers + ajout des fonctionnalités qui
> rendaient le produit « complet ». **Tout a été vérifié en live sur les 4 VM Vagrant.**

## 1. Intégration du travail de l'équipe (paternité git préservée)

`main` part de la branche fonctionnelle `alijamai` (socle complet, prouvé end-to-end). Les apports
**additifs et compatibles** des autres membres y ont été intégrés en conservant leur **auteur git** :

| Auteur | Apport |
|---|---|
| Fatiha Moltif | Expiration automatique (`expiration_manager.py` + `expiration_worker.py`) + conf `nginx` |
| Imen Mezrigui | Chiffrement Fernet des mots de passe SSH (`ssh_credentials.py`) |
| Youssef Rammeh | Tests du endpoint `/health` |

> Les réécritures concurrentes (mêmes fichiers cœur, architecture en packages incompatible) **n'ont
> pas** été fusionnées : elles auraient cassé `main`. Seules les parties réellement complémentaires
> ont été reprises.

## 2. Fonctionnalités ajoutées

### Expiration automatique (effective)
Le service de fond `expiration_worker.py` détruit périodiquement les conteneurs des locations
échues : rental → `EXPIRED`, instance → `deleted`, worker libéré.

### Chiffrement des mots de passe SSH au repos
`/rent` stocke `instance.ssh_secret` **chiffré** (Fernet, clé `INSTANCE_ENCRYPTION_KEY`) ; le secret
en clair n'est passé qu'au conteneur et remis une seule fois au client. Déchiffré à l'affichage et
lors d'une reprise. *(Résout le `TODO S9: stocker chiffré`.)*

### Quota par utilisateur
`User.max_instances` (défaut **3**). `/rent` refuse avec **`403 quota_exceeded`** au-delà du nombre
d'instances actives autorisées. Le quota se libère à l'arrêt/expiration.

### Prolongation d'une location
`POST /instances/<id>/extend` (`duration_minutes`) repousse `rentals.end_time`. Bouton
« Prolonger » + date d'expiration affichée au dashboard.

### Rôle administrateur
`User.is_admin` + décorateur `admin_required`. `/admin/monitoring` et la gestion des distributions
sont **réservés aux admins** (403 sinon). Compte admin seedé : `admin` / `admin123`.

### Interface admin des distributions
Blueprint `admin` : page `/admin/distributions` pour **lister / ajouter / activer-désactiver** les
distributions, sans passer par le seed de démarrage.

### Heartbeat réel des workers + détection de panne + reprise
- L'agent envoie un **heartbeat périodique** au controller (`POST /workers/heartbeat`) → les workers
  **s'auto-enregistrent** (plus de seeding statique).
- Le service de fond `recovery_worker.py` passe `OFFLINE` les workers muets (> 60 s) et **relance
  leurs instances** sur un autre worker.

### Migrations Flask-Migrate
`migrations/` + migration initiale. `start.py` applique `flask db upgrade` au lieu de `create_all()`
→ un changement de schéma ne détruit plus la base.

### HTTPS (nginx)
Service `nginx` (reverse proxy TLS, ports 80/443). Ansible génère un certificat auto-signé et vérifie
`https://192.168.56.10/health`.

### Résolution DNS fiable et durable (Ansible)
Premier play de `deploy.yml` : drop-in `systemd-resolved` (`DNS=8.8.8.8 1.1.1.1`) sur toutes les VM,
persistant au reboot. Corrige le DNS figé après suspension/reprise de VM.

## 3. Preuves (vérifié en live)

| Vérification | Résultat |
|---|---|
| HTTPS `https://192.168.56.10/health` (nginx/TLS) | `{"status":"ok"}` |
| Workers auto-enregistrés via heartbeat | 3 workers `AVAILABLE` |
| **Panne** : agent worker3 tué → `OFFLINE` (60 s) → instance **recréée sur worker1** → SSH OK | ✅ |
| Agent worker3 relancé → **revient `AVAILABLE`** | ✅ |
| Expiration : date de fin reculée → conteneur détruit par le worker de fond | ✅ |
| Quota : 3 locations OK, **4ᵉ → 403** | ✅ |
| Prolongation : `+60 min` → `end_time` repoussé | ✅ |
| Rôle admin : user normal → 403, admin → 200 | ✅ |
| DNS durable : OK **après reboot complet** de worker3 | ✅ |
| Migrations : base fraîche créée par `flask db upgrade` (`alembic_version`) | ✅ |

## 4. Tests automatisés

**55 tests** passent (`pytest -q`). Ajouts de cette étape :
- `tests/test_admin.py` — quota, prolongation, contrôle d'accès admin, rendu dashboard
- `tests/test_heartbeat.py` — enregistrement + revival d'un worker
- `tests/test_crypto_expiration.py` — chiffrement roundtrip + expiration des locations échues
- `tests/test_health.py` — santé (Youssef)

## 5. Accès

- **HTTPS** : `https://192.168.56.10` *(certificat auto-signé → avertissement navigateur normal)*
- **HTTP direct (debug)** : `http://192.168.56.10:8080`
- **Admin** : `admin` / `admin123` — **Démo** : `demo` / `password123`
