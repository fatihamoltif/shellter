# Ansible — Inventaire, playbooks & vérifications (S2–S3, P4)

## Contenu
- `hosts.ini` — inventaire : groupes `[controller]` et `[workers]` (worker1/2/3).
- `ansible.cfg` — pointe sur `hosts.ini`, désactive le host-key checking, user `vagrant`.
- `group_vars/all/main.yml` — connexion SSH commune (user, clé, options).
  > `group_vars/all/` est un **dossier** : P3 y ajoute `vault.yml` (secrets chiffrés Ansible Vault).
- `group_vars/controller.yml`, `group_vars/workers.yml` — variables par groupe.
- `site.yml` — **playbook maître** (S3) : enchaîne `common` → `docker.yml` → `ssh_hardening`.
- `worker.yml` — **squelette** de déploiement du Worker Agent (dossier + venv Python + unité systemd provisoire ; activé réellement en S6).
- `.ansible-lint` — configuration du linter.

## Rôles / playbooks attendus (autres membres, S3)
`site.yml` référence des composants écrits par l'équipe :
- rôle `roles/common/` (P1) · playbook `docker.yml` (P2) · rôle `roles/ssh_hardening/` (P3).
Tant qu'ils ne sont pas présents, `site.yml` ne peut pas s'exécuter en entier.

## Prérequis (à coordonner avec le Vagrantfile — P1/P2/P3)
1. Les 4 VM tournent sur le réseau privé `192.168.56.0/24` avec les IP de `docs/architecture.md`.
2. Dans le `Vagrantfile` : `config.ssh.insert_key = false` (toutes les VM partagent la clé
   « insecure » de Vagrant → une seule clé suffit pour Ansible).
   Sinon, renseigner la clé par hôte dans `ansible/host_vars/<worker>.yml`.

## Utilisation

```bash
# depuis le dossier ansible/
cd ansible

# preuve attendue de la S2 :
ansible all -m ping
# -> chaque hôte doit répondre "pong" (SUCCESS)

# vérifier les groupes
ansible controller --list-hosts
ansible workers --list-hosts
```

## Configuration des hôtes (S3)

```bash
cd ansible

# preuve attendue de la S3 : playbook idempotent
ansible-playbook site.yml            # 1er run : configure les hôtes
ansible-playbook site.yml            # 2e run : doit rester propre (changed=0)

# squelette du Worker Agent (sur les workers)
ansible-playbook worker.yml

# qualité du code
ansible-lint
```

## Vérification réseau complète (ping + SSH entre toutes les VM)

```bash
# depuis la racine du dépôt
bash scripts/check_network.sh
```

Le script teste, et sort avec le code 0 seulement si tout passe :
1. ping de ce poste vers les 4 VM ;
2. SSH de ce poste vers les 4 VM ;
3. connectivité **entre** VM (ping + port SSH 22 ouvert) pour chaque paire.
