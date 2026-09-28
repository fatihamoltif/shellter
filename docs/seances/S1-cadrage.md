# S1 — Cadrage (P4)

## Objectif (prof)
Poser les fondations écrites du projet : schéma de données et **spécification d'API**.

## Ma partie P4
Écrire le **contrat d'API** et la **stratégie de tests**, et relire le modèle de données de P3.

## Fichiers livrés
- [`docs/api.md`](../api.md) — les 13 routes : méthode, accès, entrées/sorties, codes HTTP, format
  d'erreur, énumérations, API interne de l'agent.
- [`docs/tests.md`](../tests.md) — définition du MVP + critères d'acceptation, **matrice de tests
  T01–T16**, modèle de fiche de recette + exemples remplis.

## Preuve obtenue
Une **recette qu'une autre personne peut suivre seule**, sans explication orale (fiches de recette
détaillées avec commandes exactes).

## Notes
- Relecture du `db.md` de P3 : vérifier que chaque table/statut apparaît dans une route (`api.md`)
  et un test (`tests.md`).
- `api.md` sert de contrat commun pour le développement Flask des séances S5–S6.
