# Séance S5 — Application web & authentification (P4)

> **Auteur : Jamai Ali (P4)**
>
> Ce guide explique **ce qu'on a fait en S5** (l'application Flask avec inscription, connexion,
> sessions et dashboard protégé) et **comment la lancer / la tester**, avec le *pourquoi* de chaque
> choix. **Preuve attendue** : le parcours *inscription → connexion → dashboard → déconnexion*
> fonctionne, et la CI est verte.

---

## 1. Ma partie P4 dans la S5

| Élément | Fichier | Ce que ça fait |
|---|---|---|
| **Dashboard** | `app/dashboard.py`, `templates/dashboard.html` | Page après connexion : infos utilisateur, liste des instances (vide, remplie en S6), boutons « Louer » / « Accéder ». Protégée par `login_required`. |
| **Protection CSRF** | `app/__init__.py` (`CSRFProtect`), formulaires | Chaque formulaire POST porte un jeton anti-CSRF (`hidden_tag()` / `csrf_token()`). |
| **Tests d'accès** | `tests/test_auth.py` | Sans session → redirection `/login`, mauvais mot de passe, logout, + parcours complet. |

> Pour que ma partie soit **réellement exécutable et testable**, j'ai aussi mis en place le flux
> d'auth complet (factory, register, login/sessions) — ce sont les parties de P1/P2/P3. À la fusion,
> leurs versions viendront réconcilier ce socle.

---

## 2. Architecture de l'application

```
app/
├─ __init__.py     # factory create_app : config, DB, Flask-Login, CSRF, blueprints, /health
├─ config.py       # configs development / testing / production (lues depuis l'environnement)
├─ models.py       # modèles + User étendu (UserMixin, set_password/check_password)
├─ forms.py        # formulaires Flask-WTF (RegisterForm, LoginForm) -> CSRF + validation
├─ auth.py         # blueprint auth : /register, /login, /logout
├─ dashboard.py    # blueprint dashboard : /dashboard   (P4)
└─ templates/      # base.html, login.html, register.html, dashboard.html
```

### Les routes
| Méthode | Route | Accès | Rôle |
|---|---|---|---|
| GET | `/health` | public | état de Flask + connexion à la base (200 / 503) |
| GET/POST | `/register` | public | inscription (validation + mot de passe **haché**) |
| GET/POST | `/login` | public | connexion (Flask-Login, session) |
| POST | `/logout` | connecté | déconnexion |
| GET | `/dashboard` | connecté | dashboard (P4) — sinon redirige vers `/login` |

### Choix de sécurité
- **Mots de passe hachés** (`werkzeug`), jamais stockés en clair.
- **Sessions** via Flask-Login, cookie `HttpOnly` (et `Secure` en production/HTTPS S10).
- **CSRF** activée globalement (Flask-WTF).
- Message de connexion **générique** (« Identifiants invalides ») pour ne pas révéler si c'est le
  login ou le mot de passe qui est faux.

---

## 3. Lancer l'application en local

```bash
pip install -r requirements.txt

# base SQLite locale + clé secrète
export FLASK_CONFIG=development
export SECRET_KEY="une-cle-de-dev"
export DATABASE_URL="sqlite:///shellter.db"

# créer les tables + quelques données
python -m scripts.seed

# démarrer
flask --app app run
```
Puis ouvrir <http://127.0.0.1:5000> → on est redirigé vers `/login`. On peut créer un compte,
se connecter, voir le dashboard, se déconnecter.

> ⚠️ Le validateur d'email **refuse les domaines spéciaux** (`.local`, `.test`…) : utiliser un
> vrai domaine (`@example.com`, `@gmail.com`…) à l'inscription.

---

## 4. Lancer les tests

```bash
pip install -r requirements-dev.txt
pytest -v
```
Attendu : **15 passed** — 8 tests d'authentification (S5) + 7 tests de modèles (S4).

### Ce que prouvent les tests d'accès (S5)
- `test_dashboard_requires_login` → `/dashboard` sans session redirige vers `/login`.
- `test_full_auth_journey` → inscription → connexion → dashboard (affiche le nom, liste vide).
- `test_login_wrong_password` → un mauvais mot de passe n'ouvre pas de session.
- `test_logout_closes_session` → après logout, le dashboard redirige de nouveau.
- `test_register_duplicate_email_rejected` / `test_register_short_password_rejected` → validation.
- `test_password_never_stored_in_clear` → le hash ≠ le mot de passe, `check_password` fonctionne.
- `test_health_ok` → `/health` renvoie 200.

---

## 5. Détails techniques (pièges rencontrés)
- **Emails `.local` refusés** par `email-validator` (domaine à usage spécial) → les tests utilisent
  des domaines normaux (`@example.com`).
- **SQLite en mémoire pour les tests** : chaque connexion aurait sa propre base vide. On force un
  `StaticPool` (connexion unique partagée) — uniquement pour SQLite, PostgreSQL (CI) n'est pas touché.

---

## 6. Note d'intégration pour l'équipe
Ce socle contient des parties de P1 (factory/blueprints/`/health`), P2 (register/validation) et P3
(login/sessions). Chacun réconciliera sa version avec celle-ci lors de la fusion sur `main` :
la structure (blueprints, `config.py`, `User` étendu) sert de contrat commun.
