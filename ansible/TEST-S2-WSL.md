# Guide — Tester le projet avec Vagrant + Ansible (WSL)

> **Auteur : Jamai Ali (P4)** · Séance S2 — Inventaire Ansible & vérification réseau
>
> Ce guide explique, pas à pas, **comment tester le projet de bout en bout** (créer l'infra avec
> Vagrant, puis vérifier qu'Ansible joint les machines), et surtout **pourquoi** on fait chaque
> étape. Il est écrit pour être rejoué par n'importe qui du groupe **sans explication orale** —
> c'est la « preuve attendue » de la S2.

---

## 1. Qu'est-ce qu'on cherche à prouver ?

Mon livrable S2 est composé de :
- `ansible/hosts.ini` — l'**inventaire** : la liste des machines (1 controller + 3 workers) rangées
  dans des groupes `[controller]` et `[workers]`.
- `ansible/group_vars/` — les **variables** attachées à ces machines (utilisateur SSH, IP, ports…).
- `scripts/check_network.sh` — un script qui teste le **ping + SSH entre toutes les VM**.

La **preuve officielle** demandée par la prof est : **`ansible all -m ping` réussit** sur les 4 machines.

On valide en **deux niveaux** :
- **Niveau 1 — sans VM** : vérifier que l'inventaire est bien écrit (groupes + variables corrects).
- **Niveau 2 — avec les VM** : créer l'infra avec Vagrant, puis le vrai `ansible all -m ping`.

---

## 2. Les outils et leur rôle

| Outil | Rôle | Où il tourne |
|---|---|---|
| **VirtualBox** | le moteur qui fait tourner les VM | Windows |
| **Vagrant** | crée/démarre les 4 VM à partir du `Vagrantfile` | Windows |
| **Ansible** | se connecte en SSH aux VM et les configure | Linux (**WSL**) |
| **WSL** (Ubuntu) | un vrai Linux intégré à Windows, pour lancer Ansible | Windows |

> 💡 À retenir : les commandes **Vagrant** se lancent dans **PowerShell** (Windows) ; les commandes
> **Ansible** se lancent dans **Ubuntu (WSL)**. Ne pas mélanger les deux.

---

## 3. Installation (une seule fois)

### 3.1 VirtualBox + Vagrant (dans PowerShell)
```powershell
winget install Oracle.VirtualBox     # le moteur de VM (si pas déjà installé)
winget install Hashicorp.Vagrant     # l'outil Vagrant
```
⚠️ **Après l'installation de Vagrant, ferme et rouvre PowerShell** (sinon la commande `vagrant`
n'est pas encore reconnue). Vérifie :
```powershell
vagrant --version        # doit afficher "Vagrant 2.4.x"
```

### 3.2 WSL + Ansible (dans Ubuntu)
Entre dans Ubuntu depuis PowerShell :
```powershell
wsl
```
Ton invite change (ex. `jamai@AsusRogAli:...$`) → **tu es dans Linux**. Installe Ansible :
```bash
sudo apt update
sudo apt install -y ansible
ansible --version
```

---

## 4. Niveau 1 — Tester l'inventaire SANS VM (rapide)

Vérifie que `hosts.ini` et `group_vars/` sont bien structurés. **Aucune VM requise** : on ne fait que
*lire* l'inventaire.

```bash
cd /mnt/c/Users/jamai/OneDrive/Desktop/shellter-push/ansible

# 1. la structure des groupes
ansible-inventory -i hosts.ini --graph
# attendu :
#   @all:
#     |--@shellter:
#     |  |--@controller:
#     |  |  |--controller
#     |  |--@workers:
#     |  |  |--worker1 / worker2 / worker3

# 2. les variables d'une machine (bonne IP + vars)
ansible-inventory -i hosts.ini --host worker1     # ansible_host=192.168.56.11, agent_port=5000...

# 3. la syntaxe du script réseau
bash -n ../scripts/check_network.sh && echo "script OK"
```

> **Pourquoi `/mnt/c/...`** : depuis Ubuntu, le disque `C:` de Windows est monté sous `/mnt/c`.

---

## 5. Niveau 2 — Le vrai test avec les VM (la preuve S2)

### 5.1 Démarrer les 4 VM (dans PowerShell)
```powershell
cd C:\Users\jamai\OneDrive\Desktop\shellter-push
vagrant up          # 1re fois : long (télécharge Ubuntu + crée les 4 VM)
vagrant status      # control + worker1/2/3 doivent être "running (virtualbox)"
```
**Pourquoi** : `vagrant up` lit le `Vagrantfile` et crée les 4 machines (control `192.168.56.10`,
worker1/2/3 en `.11/.12/.13`), avec `config.ssh.insert_key = false` → toutes partagent la même clé SSH.

### 5.2 Préparer la clé SSH dans WSL (dans Ubuntu)
L'inventaire cherche la clé « insecure » de Vagrant dans `~/.vagrant.d/`. On la copie depuis Windows
avec les bonnes permissions (SSH refuse une clé trop ouverte) :
```bash
mkdir -p ~/.vagrant.d
cp /mnt/c/Users/jamai/.vagrant.d/insecure_private_key ~/.vagrant.d/insecure_private_key
chmod 600 ~/.vagrant.d/insecure_private_key
```
> **Pourquoi** : Vagrant tourne côté Windows, la clé est sous `C:\Users\jamai\.vagrant.d\`. Ansible
> tourne côté WSL et lit `~/.vagrant.d/` : on aligne les deux en copiant la clé (et `chmod 600`
> sinon SSH la rejette comme « unprotected »).

### 5.3 Lancer `ansible all -m ping` (dans Ubuntu) 🎯
```bash
cd /mnt/c/Users/jamai/OneDrive/Desktop/shellter-push/ansible
ansible all -i hosts.ini -m ping
```
**Résultat attendu — la preuve S2 :**
```
controller | SUCCESS => { "changed": false, "ping": "pong" }
worker1    | SUCCESS => { "changed": false, "ping": "pong" }
worker2    | SUCCESS => { "changed": false, "ping": "pong" }
worker3    | SUCCESS => { "changed": false, "ping": "pong" }
```
**Pourquoi** : le module `ping` d'Ansible se connecte en SSH à chaque VM et vérifie que Python
répond. **4 × `SUCCESS` / `pong`** = l'inventaire ET la connexion SSH fonctionnent → **objectif S2 atteint.**

### 5.4 Vérifier le réseau entre toutes les VM (dans Ubuntu)
```bash
bash ../scripts/check_network.sh
```
**Résultat attendu** : ping + SSH du poste vers les 4 VM, puis connectivité entre les 12 paires de
VM, tous en `OK`, et pour finir : **`✅ Tous les tests réseau sont PASSÉS.`**

### 5.5 Arrêter les VM quand tu as fini (dans PowerShell)
Les 4 VM consomment de la RAM. Pour les éteindre sans les supprimer :
```powershell
cd C:\Users\jamai\OneDrive\Desktop\shellter-push
vagrant halt          # éteint les VM (relançables avec vagrant up)
# vagrant destroy -f  # (optionnel) supprime tout ; se recrée avec vagrant up
```

---

## 6. Les 2 warnings normaux (à ignorer)

### ⚠️ « Ansible is being run in a world writable directory … ignoring ansible.cfg »
On travaille sur `/mnt/c` (disque Windows), qu'Ansible juge « accessible en écriture par tous » et
refuse d'y lire `ansible.cfg` par sécurité. C'est pour ça qu'on passe `-i hosts.ini` à la main. Pas
une erreur de mon travail. (Pour t'en débarrasser : copier le projet dans `~` côté Linux.)

### ⚠️ « Found both group and host with same name: controller »
Le **groupe** `[controller]` et la **machine** `controller` portent le même nom. Bénin ; on garde ce
nom car c'est celui du sujet de la prof (page 9).

---

## 7. Récapitulatif (checklist)

| Test | Commande | VM requises ? | Preuve | Statut |
|---|---|---|---|---|
| Structure de l'inventaire | `ansible-inventory -i hosts.ini --graph` | ❌ | 2 groupes + 4 machines | ✅ validé |
| Variables d'un hôte | `ansible-inventory -i hosts.ini --host worker1` | ❌ | bonne IP + variables | ✅ validé |
| Syntaxe du script | `bash -n ../scripts/check_network.sh` | ❌ | `script OK` | ✅ validé |
| **Connexion réelle** | `ansible all -i hosts.ini -m ping` | ✅ | `SUCCESS` × 4 | ✅ **validé sur infra Vagrant** |
| Réseau inter-VM | `bash ../scripts/check_network.sh` | ✅ | tout en `OK` | ✅ **validé sur infra Vagrant** |

**Prérequis à rappeler à l'équipe** : le `Vagrantfile` doit contenir `config.ssh.insert_key = false`,
sinon chaque VM a une clé SSH différente et l'inventaire ne peut pas toutes les joindre.
