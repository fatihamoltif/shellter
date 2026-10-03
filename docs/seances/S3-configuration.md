# S3 — Configuration Ansible : playbooks (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P4 / P2+P3
> **Output prof de la séance :** un `ansible-playbook` idempotent, hôtes prêts.

---

## 1. Contexte et objectif

La S2 a créé des VM **vides**. La S3 les **configure automatiquement** avec Ansible (Docker, SSH
durci, etc.). Ma partie (P4) est le **playbook maître `site.yml`** qui orchestre les rôles des
autres, et le **squelette `worker.yml`** pour déployer le Worker Agent.

- P1 → rôle `common` · P2 → `docker.yml` · P3 → rôle `ssh_hardening` + Vault · **P4 → `site.yml` +
  `worker.yml`**.

**Preuve attendue :** `vagrant up` puis `ansible-playbook site.yml` donnent des hôtes prêts, et la
**seconde exécution reste propre (`changed=0`)** — c'est l'**idempotence**.

---

## 2. L'idempotence, c'est quoi et pourquoi

Un playbook **idempotent** peut être relancé autant de fois qu'on veut sans rien casser : Ansible
**vérifie l'état actuel** avant d'agir. 1re exécution → il installe (`changed`) ; 2e exécution → tout
est déjà en place → il ne fait **rien** (`changed=0`). C'est la garantie d'une infra **reproductible**
(contrairement à un script bash qui ré-exécute tout aveuglément).

---

## 3. Ma partie P4 en détail

### 3.1 `ansible/site.yml` — le playbook maître
Enchaîne les 3 couches de configuration **dans l'ordre** :
```yaml
- name: Socle commun à toutes les VM
  hosts: all
  become: true
  roles:
    - common                    # P1 : paquets, NTP, fuseau horaire, utilisateur shellter

- name: Installation de Docker et Compose
  ansible.builtin.import_playbook: docker.yml   # P2

- name: Durcissement SSH et pare-feu
  hosts: all
  become: true
  roles:
    - ssh_hardening             # P3 : root interdit, mot de passe off, ufw
```
> L'ordre `common → docker → ssh_hardening` est important : `docker.yml` ajoute l'utilisateur
> `shellter` (créé par `common`) au groupe docker.

### 3.2 `ansible/worker.yml` — squelette du Worker Agent
Sur chaque worker : installe Python + venv, crée `/opt/shellter/agent`, dépose une **unité systemd
provisoire** (`shellter-agent.service`) enregistrée mais non démarrée (le code de l'agent arrive en
S6). Idempotent grâce à `creates:` pour le venv.

### 3.3 `ansible/.ansible-lint`
Configuration du linter (profil `basic`) ; ne bloque pas sur les rôles non encore présents
localement (écrits par P1/P2/P3).

---

## 4. Comment tester (procédure complète)

```powershell
vagrant up                      # les 4 VM démarrent (PowerShell)
```
```bash
# WSL, depuis ansible/
ansible-galaxy collection install community.general   # requis par ssh_hardening (module ufw)

# 1re exécution : configure les hôtes
ansible-playbook -i hosts.ini site.yml --ask-vault-pass

# 2e exécution : doit rester propre (changed=0)
ansible-playbook -i hosts.ini site.yml --ask-vault-pass
```
> **`--ask-vault-pass`** : le fichier `group_vars/all/vault.yml` (secrets de P3) est chiffré avec
> Ansible Vault ; Ansible a besoin du mot de passe pour le déchiffrer (même si aucun rôle ne
> l'utilise encore, le fichier est chargé pour tous les hôtes).

---

## 5. Preuve obtenue (recap réel sur les 4 VM)

| | controller | worker1 | worker2 | worker3 |
|---|---|---|---|---|
| **Run 1** (config) | `ok=21 changed=15` | `changed=15` | `changed=15` | `changed=15` |
| **Run 2** (idempotence) | `ok=20 **changed=0**` | `changed=0` | `changed=0` | `changed=0` |

`failed=0` et `unreachable=0` sur les deux runs.

**Vérifié en vrai :** Docker installé sur les 4 VM, SSH durci (root off, mot de passe off, ufw avec
OpenSSH autorisé) **sans perdre la connexion** (auth par clé), NTP/chrony et utilisateur `shellter`
en place.

> Détail normal : le run 2 a `ok=20` (un de moins) car le handler « Reload SSH » ne s'exécute qu'en
> cas de changement → non déclenché au 2e run. C'est précisément le signe d'une vraie idempotence.

---

## 6. Notes d'intégration
- `site.yml` **référence** les composants de P1/P2/P3 ; c'est un **orchestrateur**. Les rôles
  `common`, `docker.yml` et `ssh_hardening` ont été rapatriés sur ma branche pour permettre le test.
- `community.general` est requis par le module `ufw` du rôle `ssh_hardening`.
- Le mot de passe du Vault a été fourni via un fichier temporaire hors dépôt (jamais commité).
