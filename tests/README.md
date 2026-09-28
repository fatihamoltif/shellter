# Tests & CI — Séance S4 (P4)

## Contenu
- `conftest.py` — fixtures pytest (app + base de test : PostgreSQL en CI, SQLite en mémoire en local).
- `test_models.py` — CRUD + contraintes : unicité (email/username), statut invalide (CHECK), **clé étrangère invalide**, chaîne complète des relations.
- `../scripts/seed.py` — insère 3 distributions, 1 utilisateur, 1 worker fictif.
- `../.github/workflows/ci.yml` — pipeline CI : install deps → service PostgreSQL → pytest.

## Lancer les tests en local
```bash
pip install -r requirements-dev.txt
pytest -v                       # SQLite en mémoire par défaut
```
> Le test de **clé étrangère** ne se déclenche qu'avec les FK activées : en CI (PostgreSQL) c'est
> natif ; en local (SQLite) `conftest.py` active `PRAGMA foreign_keys=ON`.

## Lancer le seed
```bash
python -m scripts.seed
```

## Preuve attendue S4 : « un run vert et un run rouge »
1. **Run vert** : pousser cette branche → l'onglet *Actions* de GitHub montre la CI ✅.
2. **Run rouge** (sur une branche de test jetable) : casser volontairement un test, par ex. dans
   `test_create_and_read_user` remplacer l'email attendu par une valeur fausse :
   ```python
   assert user.email == "faux@exemple.com"   # <-- fait échouer le test
   ```
   Committer sur une branche `test/ci-rouge`, pousser → la CI passe au **rouge** ❌, ce qui
   prouve que le pipeline **bloque** un code cassé. Puis supprimer la branche.
