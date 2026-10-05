# S2 — Infrastructure : inventaire Ansible & vérification réseau (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P3 / P2+P4
> **Output prof de la séance :** des VM qui démarrent avec Docker installable.

---

## 1. Contexte et objectif

La S2 met en place l'**infrastructure virtuelle** : 4 VM créées par Vagrant (1 controller + 3
workers) sur un réseau privé. Ma partie (P4) est l'**inventaire Ansible** — la liste des machines et
la façon de s'y connecter — et un **script de vérification réseau**.

- P1 → VM controller · P2 → worker1 + réseau · P3 → worker2/3 · **P4 → inventaire + vérifs**.

**Preuve attendue :** `ansible all -m ping` réussit sur les 4 machines.

---

## 2. Pourquoi WSL

**Ansible ne tourne pas sous Windows** (le nœud de contrôle doit être un Linux). **WSL** (*Windows
Subsystem for Linux*) est un vrai Ubuntu intégré à Windows : c'est le moyen le plus simple d'avoir
Ansible. On lance les commandes **Vagrant** dans PowerShell (Windows) et **Ansible** dans WSL.

---

## 3. Ma partie P4 en détail

### 3.1 L'inventaire (`ansible/hosts.ini`)
```ini
[controller]
controller ansible_host=192.168.56.10

[workers]
worker1 ansible_host=192.168.56.11
worker2 ansible_host=192.168.56.12
worker3 ansible_host=192.168.56.13

[shellter:children]
controller
workers
```
Les IP correspondent à `docs/architecture.md` (réseau privé `192.168.56.0/24`).

### 3.2 Les variables (`ansible/group_vars/`)
- **`all/main.yml`** : connexion SSH commune — `ansible_user: vagrant`, options SSH
  (`StrictHostKeyChecking=no`), et la **clé privée** partagée. Placé dans le **dossier** `all/`
  (et non `all.yml`) pour cohabiter avec le `vault.yml` de P3.
- **`controller.yml`** : ports 80/443 du controller.
- **`workers.yml`** : port de l'agent (`5000`), capacité (`max_instances`), plage de ports SSH
  (`20000–30000`).

### 3.3 La configuration (`ansible/ansible.cfg`)
Pointe sur `hosts.ini`, désactive le host-key checking, fixe `remote_user = vagrant`. Permet de
lancer directement `ansible all -m ping` depuis le dossier `ansible/`.

### 3.4 Le script réseau (`scripts/check_network.sh`)
Teste, et sort avec le code 0 seulement si **tout** passe :
1. **ping** de ce poste vers les 4 VM ;
2. **SSH** de ce poste vers les 4 VM ;
3. **connectivité entre VM** : pour chaque paire (source→destination), ping + port SSH 22 ouvert
   (testé via `/dev/tcp`, sans avoir besoin de clés inter-VM).

---

## 4. Comment tester (commandes exactes)

> Convention : les blocs **[PowerShell]** se lancent dans PowerShell (Windows), les blocs **[WSL]**
> se lancent dans Ubuntu (WSL). On passe de l'un à l'autre en tapant `wsl` dans PowerShell.

### 4.0 Installation (une seule fois)
**[PowerShell]** — le moteur de VM + Vagrant :
```powershell
winget install Oracle.VirtualBox
winget install Hashicorp.Vagrant
# puis FERMER et ROUVRIR PowerShell pour rafraîchir le PATH
vagrant --version
```
**[WSL]** — Ansible (dans Ubuntu, après avoir tapé `wsl`) :
```bash
sudo apt update
sudo apt install -y ansible
```

### 4.1 Démarrer les VM
**[PowerShell]**
```powershell
cd C:\Users\jamai\OneDrive\Desktop\shellter-push
vagrant up            # 1re fois : long (télécharge Ubuntu + crée les 4 VM)
vagrant status        # control + worker1/2/3 doivent être "running (virtualbox)"
```

### 4.2 Entrer dans WSL et préparer la clé SSH (une seule fois)
**[PowerShell]** → passer dans Ubuntu :
```powershell
wsl
```
**[WSL]** → copier la clé SSH partagée de Vagrant au bon endroit :
```bash
mkdir -p ~/.vagrant.d
cp /mnt/c/Users/jamai/.vagrant.d/insecure_private_key ~/.vagrant.d/insecure_private_key
chmod 600 ~/.vagrant.d/insecure_private_key
```

### 4.3 LA PREUVE : `ansible all -m ping`
**[WSL]**
```bash
cd /mnt/c/Users/jamai/OneDrive/Desktop/shellter-push/ansible
ansible all -i hosts.ini -m ping --ask-vault-pass
# -> "Vault password:" : taper  azerty  (rien ne s'affiche à la saisie) puis Entrée
```
> ⚠️ **`--ask-vault-pass` est obligatoire** : le dossier `group_vars/all/` contient le `vault.yml`
> chiffré (secrets de P3), qu'Ansible charge pour toute commande. Sans le mot de passe, erreur
> *« Attempting to decrypt but no vault secrets found »*.

### 4.4 Vérification réseau complète (n'a pas besoin du vault)
**[WSL]**
```bash
bash ../scripts/check_network.sh
```

### 4.5 (Optionnel) Niveau 1 — valider la structure sans VM
**[WSL]**
```bash
cd /mnt/c/Users/jamai/OneDrive/Desktop/shellter-push/ansible
ansible-inventory -i hosts.ini --graph          # arbre des groupes
ansible-inventory -i hosts.ini --host worker1   # IP + variables
bash -n ../scripts/check_network.sh             # syntaxe du script
```

### 4.6 Arrêter les VM quand on a fini
**[PowerShell]**
```powershell
cd C:\Users\jamai\OneDrive\Desktop\shellter-push
vagrant halt          # éteint les VM (relançables avec vagrant up)
```

---

## 5. Preuve obtenue (sortie réelle)

`ansible all -m ping` :
```
controller | SUCCESS => { "ping": "pong" }
worker1    | SUCCESS => { "ping": "pong" }
worker2    | SUCCESS => { "ping": "pong" }
worker3    | SUCCESS => { "ping": "pong" }
```
`check_network.sh` : ping + SSH du poste vers les 4 VM, puis les **12 paires** inter-VM en `OK` →
**« Tous les tests réseau sont PASSÉS. »**

---

## 6. Pièges rencontrés (et leur explication)

- **Prérequis Vagrantfile** : `config.ssh.insert_key = false` → toutes les VM partagent la clé
  « insecure » de Vagrant. Sans ça, chaque VM a une clé différente et l'inventaire (une seule clé)
  ne peut pas toutes les joindre.
- **Warning « world writable directory »** : sur `/mnt/c` (disque Windows), Ansible refuse par
  sécurité de lire le `ansible.cfg`. On passe `-i hosts.ini` à la main. Bénin.
- **Warning « group and host same name: controller »** : le groupe `[controller]` et l'hôte
  `controller` portent le même nom. Bénin ; conservé car conforme au sujet de la prof.
- **Réseau WSL2** : WSL2 est en NAT ; ici il atteint bien le réseau host-only `192.168.56.x`. En cas
  d'échec, on lance Ansible depuis la VM `control` (même réseau que les workers).
- **Vault requis depuis la S3** : le `vault.yml` chiffré (secrets de P3) étant dans `group_vars/all/`,
  toute commande Ansible réclame `--ask-vault-pass` (mot de passe `azerty`), même un simple `ping`.
  Erreur sinon : *« Attempting to decrypt but no vault secrets found »*. Le `check_network.sh`, lui,
  n'utilise pas Ansible → pas de vault.
