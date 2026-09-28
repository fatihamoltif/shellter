# S6 — API Web : location (P4)

## Objectif (prof)
Un utilisateur loue une distro et obtient un accès SSH fonctionnel.

## Ma partie P4
Écrire le **Resource Manager** (choix du worker) et l'**API de location** : `POST /rent`,
`GET /instances`, `POST /instances/<id>/stop`.

## Fichiers livrés
- [`app/resource_manager.py`](../../app/resource_manager.py) — worker `AVAILABLE` + heartbeat récent
  + capacité + **le moins chargé** ; attribution d'un port SSH libre ; passage `BUSY` si plein.
- [`app/api.py`](../../app/api.py) — `/rent` (validations → instance+rental → agent → `pending →
  creating → running`/`error`), `/instances`, `/instances/<id>/stop` (propriétaire).
- [`app/agent_client.py`](../../app/agent_client.py) — couture vers l'API du Worker Agent (mockable).
- [`tests/test_rent.py`](../../tests/test_rent.py) — 13 tests (agent mocké).

## Comment tester
```bash
pip install -r requirements-dev.txt
pytest -v          # 28 passed (13 location + 8 auth + 7 modèles)
```

## Preuve obtenue
- **Deux locations en parallèle → ports distincts** ✅
- **Instance d'un autre utilisateur → 404** ✅
- Bonus : worker absent → 503, durée invalide → 400, distro inconnue → 404, stop → rental CANCELLED.
- **CI verte** (28 tests).

## Ce qu'il reste pour le TEST MVP #1
Le parcours réel (location Ubuntu → SSH → Alpine sur un autre worker) nécessite l'agent réel de P3,
les images SSH de P1 et des workers enregistrés (P2). Ma logique est prête et branchée sur la couture
agent : il suffira de remplacer le mock par l'appel réel.
