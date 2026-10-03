# Shellter — Stratégie de tests & recette du MVP

> **Auteur :** P4 · **Séance :** S1 (Cadrage) · **Statut :** v1.
>
> Ce document définit **ce que « ça marche » veut dire** pour Shellter. Il sert de contrat de
> recette : chaque test est rejoué par **une personne qui n'en est pas l'auteur**.

---

## 1. Définition du MVP

Le MVP n'est **pas** « la page web s'affiche » ni « un conteneur démarre à la main ». Il est atteint
uniquement quand **toute la chaîne** fonctionne, de façon reproductible :

> **compte → dashboard → location → conteneur réel → SSH réel → expiration automatique**

### Jalons
- **MVP 1 (fin S6)** : inscription/connexion/déconnexion, dashboard protégé, location d'une distro
  sur un worker enregistré avec SSH fonctionnel, instances visibles avec statut + expiration + commande SSH.
  Tout tourne via `docker compose up -d`, infra créée par Vagrant + Ansible. → **tag `mvp-v1`**.
- **Version finale (fin S10)** : heartbeat + détection OFFLINE, réparation auto (conteneur tué / worker
  arrêté), expiration automatique, pipeline complet, HTTPS, supervision, SBOM. → **tag `v1.0`**.

---

## 2. Scénario de référence du MVP (à rejouer à chaque gate)

1. **Register** : créer un compte `demo` / `demo@shellter.local` / mot de passe valide → redirection `/login`.
2. **Login** → `/dashboard` s'affiche, liste d'instances vide.
3. **Louer Ubuntu** (durée courte) → le dashboard affiche l'instance `running` + la commande SSH.
4. **SSH** : `ssh user@<worker-ip> -p <port>` → connexion OK, `cat /etc/os-release` confirme Ubuntu 24.04.
5. **Louer Alpine** → l'instance part sur **un autre worker** (port distinct).
6. **Vérifier la base** : les instances sont `running`, les rentals `ACTIVE`, dates cohérentes.
7. **Stop manuel** d'une instance → conteneur absent (`docker ps -a`), rental `CANCELLED`.
8. **Expiration** : attendre la fin d'une location courte → conteneur détruit, rental `EXPIRED`, SSH refusé.

### Critères d'acceptation (mesurables, vrai/faux)
- **CA1** — après `/rent`, l'API répond `201` **et** une ligne `instances` existe en `running`.
- **CA2** — la commande SSH affichée permet réellement de se connecter au bon OS.
- **CA3** — deux locations simultanées obtiennent **deux ports différents** et **deux workers** (si dispo).
- **CA4** — la location d'un autre utilisateur renvoie `404` (jamais visible/arrêtable).
- **CA5** — à l'expiration, le conteneur n'existe plus côté Docker **et** le statut est à jour en base.

---

## 3. Matrice de tests (T01–T16)

> Reprend les 6 familles de la prof : infrastructure, configuration, application, location,
> expiration, panne. **Resp.** = qui exécute (jamais l'auteur du code testé).

| ID | Test | Résultat attendu | Quand | Resp. |
|----|------|------------------|-------|-------|
| T01 | `vagrant up` + ping | 4 VM joignables | S2, S10 | P4 |
| T02 | `site.yml` lancé 2 fois | 2ᵉ exécution `changed=0` | S3, S10 | P2 |
| T03 | Register valide / doublon | `302` / erreur affichée | S5 + CI | P2 puis P4 |
| T04 | Dashboard sans session | redirection vers `/login` | S5 + CI | P4 |
| T05 | Location Ubuntu, Debian, Alpine | `running` + SSH OK + bonne distro | S6, S10 | non-auteur |
| T06 | Instance d'un autre utilisateur | `404` / `403` | S6, S9 | P3 |
| T07 | Deux locations simultanées | ports distincts, 2 rentals | S6 | P4 puis P1 |
| T08 | Worker démarré | enregistré `AVAILABLE` automatiquement | S6 | P2 |
| T09 | Heartbeat coupé | worker `OFFLINE` en < 30 s | S7 | P1 |
| T10 | `docker kill` sur une instance | conteneur relancé, SSH restauré | S7, S10 | P2 |
| T11 | `vagrant halt worker1` | instance recréée sur worker2, user informé | S7, S10 | P4 |
| T12 | Expiration | rental `EXPIRED`, conteneur absent, SSH refusé | S7, S10 | P3 |
| T13 | Pipeline avec test cassé | merge bloqué | S4, S8 | P4, P1 |
| T14 | Commit vulnérable | bloqué par Semgrep / gitleaks / Trivy | S9 | P4 |
| T15 | Deploy + smoke | version = commit, `/health` OK en HTTPS | S10 | P2, P4 |
| T16 | Redéploiement depuis zéro | MVP complet sans bricolage | S10 | tous |

---

## 4. Modèle de fiche de recette (réutilisable)

Copier ce gabarit pour chaque exécution de test. Il doit être **suivable sans explication orale**.

```
### Fiche de recette — [ID du test]
- Pré-requis     : (infra lancée ? compte existant ? distro seedée ?)
- Étapes         : 1… 2… 3…  (une action précise par ligne)
- Commande(s)    : (curl / ssh / requête SQL exactes, copiables)
- Résultat attendu : (ce qu'on doit voir, précisément)
- Résultat obtenu  : ______
- Verdict        : ✅ / ❌   —  Gravité si ❌ : bloquant / important / cosmétique
- Testeur (non-auteur) : ______   Date : ______   Commit : ______
```

---

## 5. Exemples de fiches remplies (pour montrer le niveau de détail attendu)

### Fiche T04 — Dashboard sans session
- **Pré-requis** : stack lancée (`docker compose up -d`), aucun cookie de session.
- **Étapes** : 1) ouvrir une fenêtre privée ; 2) aller sur `/dashboard`.
- **Commande** : `curl -i http://localhost/dashboard`
- **Résultat attendu** : `HTTP/1.1 302 Found` avec `Location: /login`.
- **Verdict** : ✅ / ❌ …

### Fiche T05 — Location Ubuntu + SSH
- **Pré-requis** : compte `demo` connecté, distribution Ubuntu `enabled`, ≥ 1 worker `AVAILABLE`.
- **Étapes** : 1) se connecter ; 2) louer Ubuntu 30 min ; 3) copier la commande SSH ; 4) se connecter ; 5) vérifier l'OS.
- **Commandes** :
  ```
  # après clic "Louer" dans le dashboard, ou en direct :
  curl -i -b cookies.txt -d "distribution_id=1&duration_minutes=30" http://localhost/rent
  ssh user@192.168.56.11 -p 20012
  cat /etc/os-release      # doit afficher Ubuntu 24.04
  ```
- **Résultat attendu** : `201`, instance `running`, SSH OK, `NAME="Ubuntu"` `VERSION="24.04"`.
- **Verdict** : ✅ / ❌ …

### Fiche T07 — Deux locations simultanées
- **Pré-requis** : ≥ 2 workers `AVAILABLE`, 2 sessions utilisateur (ou 2 locations rapprochées).
- **Étapes** : 1) lancer 2 `/rent` quasi simultanés ; 2) comparer les ports et workers ; 3) vérifier la base.
- **Vérification base** :
  ```sql
  SELECT id, worker_id, ssh_port, status FROM instances ORDER BY id DESC LIMIT 2;
  ```
- **Résultat attendu** : 2 `ssh_port` **différents**, 2 `rentals` `ACTIVE` ; aucun conteneur orphelin.
- **Verdict** : ✅ / ❌ …

---

## 6. Niveaux de tests (rappel)

- **Unitaires** : validation des paramètres, calcul du TTL/expiration, sélection d'image, Resource Manager.
- **Composant** : base seule, agent seul, Flask seul, Nginx seul.
- **Intégration** : Flask ↔ PostgreSQL, Flask ↔ agent, Nginx ↔ Flask.
- **E2E** : navigateur/curl → Nginx → Flask → agent → Docker → SSH → expiration.
- **Panne** : worker OFFLINE, conteneur tué, base indisponible, port occupé, image invalide.
- **Redéploiement** : infra détruite puis recréée depuis le dépôt (T16).
