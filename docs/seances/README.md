# Journal des séances — Shellter (P4 · Jamai Ali)

Ce dossier rassemble, séance par séance, **ma partie (P4)** du projet Shellter : ce qui a été fait,
comment le tester, et la preuve obtenue.

| Séance | Thème | Ma partie P4 | Preuve | Statut |
|---|---|---|---|---|
| [S1](S1-cadrage.md) | Cadrage | Contrat d'API + stratégie de tests | Recette suivable seul | ✅ |
| [S2](S2-infrastructure.md) | Vagrant / Ansible | Inventaire + vérification réseau | `ansible all -m ping` (4 VM) | ✅ |
| [S3](S3-configuration.md) | Ansible | `site.yml` + `worker.yml` | `site.yml` idempotent (`changed=0`) | ✅ |
| [S4](S4-base-de-donnees.md) | Base de données | Seed + tests + pipeline CI | CI verte + run rouge | ✅ |
| [S5](S5-authentification.md) | API Web : auth | Dashboard + CSRF + tests d'accès | CI verte (15 tests) | ✅ |
| [S6](S6-location.md) | API Web : location | Resource Manager + `/rent` | CI verte (28 tests) | ✅ |
| [S7](S7-resilience.md) | Résilience / HA | Reprise sur un autre worker | CI verte (33 tests) | ✅ |
| [S8](S8-ci.md) | Déploiement complet & CI | Tests d'intégration (docker compose) | CI verte (2 jobs) | ✅ |
| [S9](S9-securite.md) | Sécurité intégrée (DevSecOps) | Commit piège `demo-vuln` + docs | 3 échecs distincts | ✅ |

## Documents de référence (hors journal)
- Contrat d'API : [`docs/api.md`](../api.md)
- Modèle de données (P3) : [`docs/db.md`](../db.md)
- Architecture : [`docs/architecture.md`](../architecture.md)
- Usage opérationnel Ansible : [`ansible/README.md`](../../ansible/README.md)

## Dépôt & branche
Tout mon travail est sur la branche **`alijamai`** de `fatihamoltif/shellter`. La CI (GitHub Actions)
est verte pour les séances S4, S5 et S6.
