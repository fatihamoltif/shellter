# S9 — Sécurité intégrée (DevSecOps) (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P3 / P2+P4
> **Output prof de la séance :** pipeline qui bloque un commit contenant une vulnérabilité volontaire.

---

## 1. Contexte et objectif

La S9 intègre la **sécurité dans le pipeline** (DevSecOps) : à chaque push, des scans automatiques
refusent le code vulnérable. Ma partie (P4) : le **commit piège** — une branche `demo-vuln` qui
cumule 3 failles — et sa **documentation** (`docs/securite.md`).

- P1 → Semgrep (SAST) · P2 → Trivy (scan images) · P3 → gitleaks (secrets) · **P4 → commit piège + démo**.

**Preuve attendue :** **3 échecs distincts** du pipeline, chacun expliqué dans `docs/securite.md`.

---

## 2. La chaîne de sécurité (3 scans)

Pour que ma démo soit démontrable, j'ai mis en place les 3 scans dans la CI, en **3 jobs
indépendants** (pour que chaque faille échoue séparément) :

| Job | Outil | Attrape |
|---|---|---|
| `Sécurité — SAST` | **Semgrep** | failles de **code** (injection SQL, XSS…) |
| `Sécurité — Secrets` | **gitleaks** | **secrets commités** (clés, mots de passe) |
| `Sécurité — Image` | **Trivy** | **CVE CRITICAL** dans l'image Docker |

Semgrep combine les règles publiques `p/python` + `p/flask` et une **règle custom**
(`.semgrep/sql-injection.yml`, ERROR) ciblant le SQL construit par f-string / concaténation.

---

## 3. Ma partie P4 : la branche `demo-vuln`

Trois failles volontaires, chacune déclenchant un scan **différent** :

| Faille | Fichier | Bloquée par |
|---|---|---|
| Injection SQL (`text(f"...")`) | `app/search.py` | **Semgrep** |
| Clé AWS en dur | `app/secrets_leak.py` | **gitleaks** |
| Dépendance CVE (`PyYAML==5.3.1`, 9.8) | `requirements.txt` | **Trivy** |

Chaque faille et **son correctif** sont documentés dans [`docs/securite.md`](../securite.md).

---

## 4. Preuve obtenue (confirmée sur la CI)

Sur `demo-vuln`, l'onglet Actions montre **3 échecs distincts** :
```
Sécurité — SAST (Semgrep)    ❌ failure   (injection SQL)
Sécurité — Secrets (gitleaks) ❌ failure   (clé AWS en dur)
Sécurité — Image (Trivy)      ❌ failure   (CVE CRITICAL PyYAML)
Tests / Intégration           ✅ success   (l'app fonctionne toujours)
```
Sur `alijamai` (code propre), les **5 jobs sont verts** → les scans ne produisent pas de faux
positif. La démo peut être rejouée devant l'équipe, puis la branche corrigée repasse au vert.

---

## 5. Comment rejouer la démo
```bash
# la branche demo-vuln existe déjà (gardée pour la soutenance)
# pour la recréer :
git checkout -b demo-vuln alijamai
# introduire les 3 failles (voir docs/securite.md §2), puis :
git push origin demo-vuln          # -> onglet Actions : 3 jobs sécurité rouges
# nettoyage après la soutenance :
git push origin --delete demo-vuln
```

---

## 6. Note d'intégration
Les 3 scans (Semgrep, gitleaks, Trivy) sont les parties de P1/P2/P3 ; je les ai ajoutés au pipeline
pour rendre ma démo réelle. Ils se réconcilieront avec leurs versions à la fusion sur `main`. La
branche `demo-vuln` est **conservée volontairement** (support de démonstration), contrairement à la
branche jetable du « run rouge » de la S4.
