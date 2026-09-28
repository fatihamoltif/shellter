# S5 — API Web : authentification (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P3 / P2+P4
> **Output prof de la séance :** login et signup fonctionnels de bout en bout.

---

## 1. Contexte et objectif

La S5 construit l'**application web** : inscription, connexion, sessions, dashboard protégé. Ma
partie (P4) est le **dashboard**, la **protection CSRF** et les **tests d'accès**. Comme ces éléments
sont indissociables du flux d'authentification, j'ai mis en place l'ensemble du flux (factory,
register, login/sessions) pour que ma partie soit **réellement exécutable et testable**.

- P1 → structure Flask (factory, blueprints, `/health`) · P2 → register · P3 → login/sessions ·
  **P4 → dashboard + CSRF + tests d'accès**.

**Preuve attendue :** parcours inscription → connexion → dashboard → déconnexion, **CI verte**.

---

## 2. Architecture de l'application

```
app/
├─ __init__.py     # factory create_app : config, DB, Flask-Login, CSRF, blueprints, /health
├─ config.py       # configs development / testing / production (variables d'environnement)
├─ models.py       # User étendu (UserMixin, set_password/check_password)
├─ forms.py        # formulaires Flask-WTF (RegisterForm, LoginForm) -> CSRF + validation
├─ auth.py         # blueprint auth : /register, /login, /logout
├─ dashboard.py    # blueprint dashboard : /dashboard   (P4)
└─ templates/      # base, login, register, dashboard
```

### La factory `create_app`
Assemble : configuration par environnement, `db`, `migrate`, **Flask-Login** (`LoginManager` +
`user_loader`), **CSRFProtect**, enregistrement des blueprints, route `/` (redirige vers le
dashboard) et `/health` (vérifie la connexion à la base).

### Les routes
| Méthode | Route | Accès | Rôle |
|---|---|---|---|
| GET | `/health` | public | état Flask + base (200 / 503) |
| GET/POST | `/register` | public | inscription (validation + hachage) |
| GET/POST | `/login` | public | connexion (session Flask-Login) |
| POST | `/logout` | connecté | déconnexion |
| GET | `/dashboard` | connecté | **dashboard (P4)** — sinon redirige `/login` |

### Choix de sécurité
- **Mots de passe hachés** (`werkzeug`), jamais en clair.
- **Sessions** Flask-Login, cookie `HttpOnly` (`Secure` en production/HTTPS S10).
- **CSRF** globale (Flask-WTF) ; message de login **générique** (« Identifiants invalides »).

---

## 3. Ma partie P4 en détail

- **`dashboard.py` + `templates/dashboard.html`** : page protégée par `login_required` affichant le
  nom/email, la liste des instances (vide pour l'instant, remplie en S6) et les boutons « Louer une
  instance » / « Accéder à mon instance ». Bouton de déconnexion en POST (avec jeton CSRF).
- **CSRF** : `CSRFProtect` initialisé dans la factory ; chaque formulaire porte le jeton
  (`hidden_tag()` / `csrf_token()`).
- **`tests/test_auth.py`** (8 tests d'accès) :

| Test | Ce qu'il prouve |
|---|---|
| `test_dashboard_requires_login` | `/dashboard` sans session → redirige `/login` |
| `test_full_auth_journey` | inscription → connexion → dashboard (nom affiché, liste vide) |
| `test_login_wrong_password` | mauvais mot de passe → pas de session |
| `test_logout_closes_session` | après logout, le dashboard redirige de nouveau |
| `test_register_duplicate_email_rejected` | email en doublon refusé |
| `test_register_short_password_rejected` | mot de passe < 8 refusé |
| `test_password_never_stored_in_clear` | hash ≠ mot de passe, `check_password` OK |
| `test_health_ok` | `/health` → 200 |

---

## 4. Comment tester

```bash
pip install -r requirements-dev.txt
pytest -v          # 15 passed (8 auth S5 + 7 modèles S4)
```

### Lancer l'application
```bash
export FLASK_CONFIG=development
export SECRET_KEY="une-cle-de-dev"
export DATABASE_URL="sqlite:///shellter.db"
python -m scripts.seed
flask --app app run          # http://127.0.0.1:5000
```
> Le validateur d'email **refuse les domaines spéciaux** (`.local`, `.test`) : utiliser un vrai
> domaine (`@example.com`) à l'inscription.

---

## 5. Preuve obtenue
Parcours **inscription → connexion → dashboard → déconnexion** fonctionnel ; **15 tests verts** en
local et en **CI** (le « test de fin de séance » de la prof).

---

## 6. Pièges rencontrés
- **Emails `.local` refusés** par `email-validator` (domaine à usage spécial) → tests avec
  `@example.com`.
- **SQLite en mémoire pour les tests** : chaque connexion aurait sa propre base vide → on force un
  `StaticPool` (connexion unique partagée), **uniquement** pour SQLite ; PostgreSQL (CI) n'est pas
  touché.

## 7. Note d'intégration
Ce socle contient des parties de P1 (factory/`/health`), P2 (register) et P3 (login). P1 a par
ailleurs restructuré l'app en packages (`app/api/`, `app/workers/`). La réconciliation se fera sur
`main` ; la structure (blueprints, `config.py`, `User` étendu) sert de contrat commun.
