# Branche `kubernetes-equipe` — faire apparaître le nom de chacun

Les patches sont **déjà dans le dépôt** (dossier `patches/`). Chacun applique **sa**
partie et fait **son** commit sur **son** ordinateur → `git log` montrera les 4 vrais noms.

> Les patches sont **indépendants** (fichiers différents) : ils s'appliquent sans conflit.
> On commite quand même **un par un** (chacun après que le précédent a poussé) pour éviter
> un rejet `git push` sur la branche partagée.

## 0. Chacun vérifie son identité git (une seule fois)
```bash
git config user.name  "Prénom Nom"
git config user.email "son.email@..."
```

## 1. Fatiha (P1)
```bash
git checkout kubernetes-equipe
git pull
git apply patches/P1-fatihamoltif.diff
git add -A
git commit -m "k8s(P1): cluster k3s server (Ansible) + RBAC + Secret/ConfigMap"
git push
```

## 2. Youssef (P2) — après que Fatiha a poussé
```bash
git checkout kubernetes-equipe
git pull
git apply patches/P2-YOUSSEF4315.diff
git add -A
git commit -m "k8s(P2): agents k3s + PostgreSQL (StatefulSet/PVC) + client API Kubernetes"
git push
```

## 3. Imen (P3) — après Youssef
```bash
git checkout kubernetes-equipe
git pull
git apply patches/P3-imenmezrigui.diff
git add -A
git commit -m "k8s(P3): Deployment Flask (probes) + expiration (CronJob)"
git push
```

## 4. Ali (P4) — en dernier
```bash
git checkout kubernetes-equipe
git pull
git apply patches/P4-JamaiAli.diff
git add -A
git commit -m "k8s(P4): Ingress HTTPS, /rent+stop via API K8s, reconciliation, CI, docs"
git push
```

## 5. Vérifier
```bash
git log --pretty="%an  —  %s" -4
```
→ doit afficher les 4 noms, un par partie.

## 6. (Optionnel) nettoyer
Une fois les 4 commits faits, on peut supprimer ce dossier :
```bash
git rm -r patches && git commit -m "chore: retrait des patches d'amorçage" && git push
```

---
**Windows / PowerShell** : lancer les commandes sur des lignes séparées (pas de `&&`).
**Mac / Linux / Git Bash** : `&&` fonctionne.
