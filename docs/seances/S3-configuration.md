# S3 — Configuration Ansible : playbooks (P4)

## Objectif (prof)
Un `ansible-playbook` **idempotent**, hôtes prêts.

## Ma partie P4
Écrire le **playbook maître `site.yml`** (qui enchaîne les rôles) et le **squelette `worker.yml`**
(déploiement du Worker Agent), puis lancer `ansible-lint`.

## Fichiers livrés
- [`ansible/site.yml`](../../ansible/site.yml) — enchaîne `common` (P1) → `docker.yml` (P2) →
  `ssh_hardening` (P3).
- [`ansible/worker.yml`](../../ansible/worker.yml) — squelette agent : dossier, venv Python, unité
  systemd provisoire (activée en S6).
- [`ansible/.ansible-lint`](../../ansible/.ansible-lint) — configuration du linter.

## Comment tester
```bash
# VM démarrées (vagrant up), depuis ansible/ dans WSL :
ansible-galaxy collection install community.general   # requis par ssh_hardening (ufw)
ansible-playbook -i hosts.ini site.yml --ask-vault-pass   # 1er run
ansible-playbook -i hosts.ini site.yml --ask-vault-pass   # 2e run -> changed=0
```
> `--ask-vault-pass` : le fichier `group_vars/all/vault.yml` (secrets de P3) est chiffré.

## Preuve obtenue
`site.yml` exécuté 2× sur les 4 VM :
- **Run 1** : `ok=21 changed=15` (Docker installé, SSH durci, ufw)
- **Run 2** : `ok=20 **changed=0**` → **idempotence prouvée**, `failed=0`, `unreachable=0`.

## Notes d'intégration
Les rôles `common` / `docker.yml` / `ssh_hardening` viennent de P1 / P2 / P3 ; `site.yml` est
l'orchestrateur. La preuve d'idempotence a été rejouée avec succès sur l'infra réelle.
