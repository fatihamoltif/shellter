# S2 — Infrastructure : inventaire Ansible & réseau (P4)

## Objectif (prof)
Des VM qui démarrent avec Docker installable.

## Ma partie P4
Écrire l'**inventaire Ansible** (groupes `[controller]` / `[workers]`) et un **script de
vérification réseau** (ping + SSH entre toutes les VM).

## Fichiers livrés
- [`ansible/hosts.ini`](../../ansible/hosts.ini) — inventaire, IP `192.168.56.10–13`.
- [`ansible/group_vars/`](../../ansible/group_vars) — variables communes (SSH) + par rôle.
- [`ansible/ansible.cfg`](../../ansible/ansible.cfg) — pour lancer directement `ansible all -m ping`.
- [`scripts/check_network.sh`](../../scripts/check_network.sh) — teste ping + SSH entre toutes les VM.

## Comment tester (avec WSL, car Ansible ne tourne pas sous Windows)
Prérequis : **VirtualBox + Vagrant** (Windows) et **WSL Ubuntu + Ansible**.
```bash
# 1) démarrer les VM (PowerShell)
vagrant up

# 2) préparer la clé SSH partagée dans WSL
mkdir -p ~/.vagrant.d
cp /mnt/c/Users/<user>/.vagrant.d/insecure_private_key ~/.vagrant.d/insecure_private_key
chmod 600 ~/.vagrant.d/insecure_private_key

# 3) la preuve S2
cd /mnt/c/.../shellter-push/ansible
ansible all -i hosts.ini -m ping        # -> 4x SUCCESS
bash ../scripts/check_network.sh        # -> tous les tests réseau PASSÉS
```
> **Prérequis Vagrantfile** : `config.ssh.insert_key = false` (toutes les VM partagent la même clé).
> **Warning** « world writable » sur `/mnt/c` : bénin, on passe `-i hosts.ini` à la main.

## Preuve obtenue
`ansible all -m ping` → **4× SUCCESS** (controller + worker1/2/3) sur infra Vagrant réelle, et
`check_network.sh` → tous les tests (ping + SSH inter-VM) **PASSÉS**.
