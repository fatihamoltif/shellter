# S1 — Cadrage (P4)

> **Auteur : Jamai Ali (P4)** · Binômes d'intégration : P1+P2 / P3+P4
> **Output prof de la séance :** schéma DB + spécification d'API écrits.

---

## 1. Contexte et objectif

La S1 est la séance de **cadrage collectif** : on fige les contrats qui éviteront les divergences
techniques coûteuses plus tard. On ne code presque rien ; on écrit les **fondations**.

Répartition de la séance :
- **P1** — dépôt, arborescence, `.gitignore`, `.env.example`, stratégie de branches.
- **P2** — architecture & réseau (schéma, IP/ports, flux).
- **P3** — modèle de données (les 5 tables, statuts, cycle de vie).
- **P4 (moi)** — **contrat d'API** + **stratégie de tests**, et **relecture du modèle de P3**.

---

## 2. Ma partie P4 en détail

### 2.1 Le contrat d'API (`docs/api.md`)
J'ai écrit la spécification des **13 routes** de la plateforme. Pour chaque route : la méthode HTTP,
le niveau d'accès, les champs d'entrée (avec types et règles), les réponses (codes + corps JSON) et
les cas d'erreur.

**Conventions posées :**
- **Accès** : `public`, `connecté` (session), `propriétaire`, `admin`, `token agent`.
- **Codes HTTP** normalisés : `200/201` succès, `302` redirection navigateur, `400` params,
  `401` non connecté, `403` interdit, `404` inexistant/appartient à un autre, `409` doublon,
  `422` validation métier, `503` dépendance indisponible.
- **Format d'erreur JSON** : `{ "error": "code", "message": "..." }`.

**Récapitulatif des routes :**

| # | Méthode | Route | Accès |
|---|---|---|---|
| 1 | GET | `/health` | public |
| 2 | GET/POST | `/register` | public |
| 3 | GET/POST | `/login` | public |
| 4 | POST | `/logout` | connecté |
| 5 | GET | `/dashboard` | connecté |
| 6 | GET | `/instances` | connecté |
| 7 | POST | `/rent` | connecté |
| 8 | POST | `/instances/{id}/stop` | propriétaire |
| 9 | GET | `/workers` | admin |
| 10 | GET | `/workers/{id}` | admin |
| 11 | POST | `/workers/register` | token agent |
| 12 | POST | `/workers/heartbeat` | token agent |
| 13 | GET | `/admin/monitoring` | admin (S10) |

> Le contrat inclut aussi l'**API interne de l'agent** (`POST /containers`, `DELETE
> /containers/{id}`, `GET /containers`), appelée uniquement par Flask.

### 2.2 La stratégie de tests (`docs/tests.md`)
- **Définition stricte du MVP** : *compte → dashboard → location → conteneur réel → SSH réel →
  expiration*. Une page web seule ou un conteneur lancé à la main ne comptent pas.
- **Critères d'acceptation** mesurables (vrai/faux) : CA1…CA5.
- **Matrice de tests T01–T16** couvrant les 6 familles de la prof : infrastructure, configuration,
  application, location, expiration, panne. Chaque test est rejoué par une personne **non-auteure**.
- **Modèle de fiche de recette** réutilisable + 3 fiches déjà remplies (T04, T05, T07) pour montrer
  le niveau de détail attendu (commandes exactes copiables).

### 2.3 Relecture du modèle de P3
Vérifications faites sur `docs/db.md` :
- chaque **statut** (`instances`, `rentals`, `workers`) est atteignable et testé quelque part ;
- chaque **champ** nécessaire aux tests existe (`end_time` pour l'expiration, `ssh_port`, `status`) ;
- cohérence : l'expiration est portée par `rentals.end_time`, pas par la table `instances`.

---

## 3. Fichiers livrés
- [`docs/api.md`](../api.md) — contrat d'API v1 complet.
- [`docs/tests.md`](../tests.md) — MVP + critères + matrice T01–T16 + fiches de recette.

---

## 4. Preuve obtenue
**Une recette qu'une autre personne peut suivre seule**, sans explication orale : les fiches de
recette contiennent les commandes exactes (`curl`, `ssh`, requêtes SQL) et les résultats attendus.

---

## 5. Décisions à retenir
- `api.md` devient le **contrat commun** : toute divergence code ↔ doc est un bug.
- Les durées de location autorisées et le mode d'accès aux routes `workers` ont été laissés à caler
  avec l'équipe (tranché en S6 : durées `{30, 60, 120}` min).
- Signalé à l'équipe : l'`architecture.md` initiale (P2) était en retard d'une version (2 workers au
  lieu de 3, pas d'Alpine, HTTP au lieu de HTTPS) → corrigée pour être conforme au sujet.
