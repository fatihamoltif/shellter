# Ansible — Inventaire & vérifications réseau (S2, P4)

## Contenu
- `hosts.ini` — inventaire : groupes `[controller]` et `[workers]` (worker1/2/3).
- `ansible.cfg` — pointe sur `hosts.ini`, désactive le host-key checking, user `vagrant`.
- `group_vars/all.yml` — connexion SSH commune (user, clé, options).
- `group_vars/controller.yml`, `group_vars/workers.yml` — variables par rôle.

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

## Vérification réseau complète (ping + SSH entre toutes les VM)

```bash
# depuis la racine du dépôt
bash scripts/check_network.sh
```

Le script teste, et sort avec le code 0 seulement si tout passe :
1. ping de ce poste vers les 4 VM ;
2. SSH de ce poste vers les 4 VM ;
3. connectivité **entre** VM (ping + port SSH 22 ouvert) pour chaque paire.
