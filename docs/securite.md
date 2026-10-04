# Sécurité intégrée (DevSecOps) — Séance S9 (P4)

> **Auteur : Jamai Ali (P4)**
>
> Ce document décrit la **chaîne de sécurité du pipeline** et la **branche de démonstration
> `demo-vuln`** qui cumule 3 vulnérabilités volontaires, en montrant **quelle étape bloque chaque
> problème** et **comment le corriger**. Preuve attendue : **3 échecs distincts du pipeline**.

---

## 1. La chaîne de sécurité (job `security` de la CI)

Trois scans complémentaires, chacun bloquant (`exit-code 1` en cas de problème) :

| Étape | Outil | Ce qu'elle attrape |
|---|---|---|
| **SAST** | **Semgrep** | failles dans le **code** (injection SQL, XSS, mauvais patterns) |
| **Secrets** | **gitleaks** | **secrets commités** (clés API, mots de passe en dur) |
| **Scan image** | **Trivy** | **CVE CRITICAL** dans l'image Docker (OS + dépendances) |

Semgrep utilise les règles publiques `p/python` + `p/flask` **et** une règle custom
(`.semgrep/sql-injection.yml`, sévérité ERROR) ciblant les requêtes SQL construites par
f-string / concaténation.

---

## 2. La branche `demo-vuln` : 3 vulnérabilités volontaires

On part de `alijamai` et on introduit **3 failles**, chacune déclenchant un scan différent :

| # | Vulnérabilité | Où | Étape qui bloque |
|---|---|---|---|
| 1 | **Injection SQL** (requête `text(f"...")` avec saisie utilisateur) | `app/api.py` | **Semgrep** (SAST) |
| 2 | **Secret en dur** (fausse clé AWS) | `app/secrets_leak.py` | **gitleaks** |
| 3 | **Dépendance vulnérable** dans l'image (`PyYAML==5.3.1`, CVE-2020-14343, 9.8) | `requirements.txt` | **Trivy** |

### Détail et correctif de chaque faille

**1. Injection SQL (Semgrep)**
```python
# FAILLE — la saisie utilisateur est injectée directement dans la requête
q = text(f"SELECT * FROM users WHERE username = '{username}'")
db.session.execute(q)
```
- **Bloqué par :** Semgrep (règle `shellter-sql-injection-raw`, ERROR).
- **Correctif :** requête **paramétrée** / ORM :
  ```python
  User.query.filter_by(username=username).first()
  # ou : db.session.execute(text("... WHERE username = :u"), {"u": username})
  ```

**2. Secret en dur (gitleaks)**
```python
# FAILLE — une clé secrète ne doit JAMAIS être dans le code
AWS_ACCESS_KEY_ID = "AKIA2E4XZ9QWERTY1234"
AWS_SECRET_ACCESS_KEY = "wJalrXabc123FEMI+K7MDENGbPxRfiCYsecretKEY"
```
- **Bloqué par :** gitleaks.
- **Correctif :** passer par une **variable d'environnement**, un **Secret CI**, ou **Ansible Vault** —
  jamais en clair dans le dépôt. Et **révoquer** la clé exposée.

**3. Image vulnérable (Trivy)**
```
# requirements.txt — FAILLE : dépendance obsolète avec CVE CRITICAL
PyYAML==5.3.1            # CVE-2020-14343 (9.8) — corrigé en 5.4
```
- **Bloqué par :** Trivy (gate `CRITICAL`).
- **Correctif :** **mettre à jour** la dépendance (`PyYAML>=5.4`) ; de même, utiliser une **image de
  base récente** (`python:3.12-slim`), slim, utilisateur non-root, sans secret dans le Dockerfile.

---

## 3. Preuve : 3 échecs distincts (confirmé)

La sécurité est découpée en **3 jobs indépendants**, donc chaque faille échoue **séparément**.
Sur la branche `demo-vuln`, l'onglet Actions montre :

| Job | Résultat | Faille |
|---|---|---|
| Sécurité — SAST (Semgrep) | ❌ failure | injection SQL |
| Sécurité — Secrets (gitleaks) | ❌ failure | clé AWS en dur |
| Sécurité — Image (Trivy) | ❌ failure | CVE CRITICAL (PyYAML) |
| Tests / Intégration | ✅ success | (l'application fonctionne toujours) |

→ **3 échecs distincts**, un par outil. Les jobs `test`/`integration` restent verts : les failles
sont bien attrapées par la **sécurité**, pas en cassant le fonctionnement. Chaque faille corrigée
(voir §2) fait repasser son job au **vert**.

---

## 4. Comment rejouer la démo
```bash
# créer/mettre à jour la branche de démo (depuis alijamai)
git checkout -b demo-vuln alijamai
# ... introduire les 3 failles (voir §2) ...
git commit -am "demo: 3 vulnerabilites volontaires" && git push origin demo-vuln
# -> onglet Actions : le job "security" est rouge sur les 3 étapes
# nettoyage après la démo :
git checkout alijamai && git push origin --delete demo-vuln
```

## 5. Bonnes pratiques de sécurité déjà en place (hors démo)
- Mots de passe **hachés** (werkzeug), jamais en clair.
- Secrets via **Ansible Vault** (chiffré) et variables d'environnement.
- Requêtes via l'**ORM SQLAlchemy** (pas de SQL concaténé), auto-échappement **Jinja** (anti-XSS).
- **CSRF** activée (Flask-WTF), cookies `HttpOnly`.
- Image Docker **slim**, **utilisateur non-root**, aucun secret dans le Dockerfile.
- Contrôle d'accès : une instance d'un autre utilisateur renvoie **404** (testé).
---

## 6. Verification du code reel (P1)

En plus de la chaine de securite CI et de la demo `demo-vuln`, un scan Semgrep
a ete lance manuellement sur le code applicatif reel (`app/`, hors branche
demo) avec la meme configuration (`.semgrep` + `p/python` + `p/flask`) :

- **56 regles executees sur 13 fichiers, 0 finding.**
- Aucune requete SQL construite par concatenation/f-string : tout passe par
  l'ORM SQLAlchemy (`Model.query.filter_by(...)`) ou des requetes
  parametrees (`text(...)`, binds).
- Echappement Jinja verifie actif : aucun filtre `|safe`, aucun
  `autoescape(False)`, aucun `Markup()` ni `render_template_string` dans le
  code.

Rapport complet : `semgrep-report.json` (genere par `semgrep scan ... --json`).
