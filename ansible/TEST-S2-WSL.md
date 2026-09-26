# Guide — Tester mon rendu S2 avec WSL

> **Auteur : Jamai Ali (P4)** · Séance S2 — Inventaire Ansible & vérification réseau
>
> Ce guide explique, pas à pas, **comment prouver que mon travail de la S2 fonctionne**, et
> surtout **pourquoi** on fait chaque étape. Il est écrit pour moi (et pour toute personne du
> groupe qui voudra rejouer le test sans explication orale — c'est la « preuve attendue » de la S2).

---

## 1. Qu'est-ce qu'on cherche à prouver ?

Mon livrable S2 est composé de :
- `ansible/hosts.ini` — l'**inventaire** : la liste des machines (1 controller + 3 workers) rangées
  dans des groupes `[controller]` et `[workers]`.
- `ansible/group_vars/` — les **variables** attachées à ces machines (utilisateur SSH, IP, ports…).
- `scripts/check_network.sh` — un script qui teste le **ping + SSH entre toutes les VM**.

La **preuve officielle** demandée par la prof est : **`ansible all -m ping` réussit** sur les 4 machines.

On va valider ça en **deux niveaux** :
- **Niveau 1 — sans VM** : vérifier que l'inventaire est bien écrit (groupes + variables corrects).
  Ça se fait tout de suite, ça prouve que *mon* fichier est bon.
- **Niveau 2 — avec les VM** : le vrai `ansible all -m ping`, quand l'infrastructure Vagrant tourne.

---

## 2. Pourquoi WSL ?

**Ansible ne fonctionne pas sous Windows** (le « control node » qui pilote les machines doit être un
Linux). **WSL** (*Windows Subsystem for Linux*) est un vrai Ubuntu intégré à Windows : c'est la
manière la plus simple d'avoir Ansible sur un PC Windows, sans machine virtuelle séparée.

> 💡 À retenir : on tape les commandes **Windows** dans PowerShell, et les commandes **Linux**
> (`ansible`, `sudo`, `apt`…) dans **Ubuntu (WSL)**. Ne pas mélanger les deux.

---

## 3. Préparation (une seule fois)

### 3.1 Entrer dans Ubuntu
Dans **PowerShell**, tape :
```powershell
wsl
```
L'invite change (ex. `jamai@AsusRogAli:...$`). **À partir de là, tu es dans Linux.**
*(Si tu revois une erreur du type « `&&` n'est pas un séparateur valide », c'est que tu es ressorti
dans PowerShell : retape `wsl`.)*

### 3.2 Installer Ansible (dans Ubuntu)
```bash
sudo apt update
sudo apt install -y ansible
ansible --version      # vérifie que c'est bien installé
```
**Pourquoi** : `apt` est le gestionnaire de paquets d'Ubuntu ; il télécharge et installe Ansible.

---

## 4. Niveau 1 — Tester l'inventaire SANS VM (tout de suite)

Ce niveau vérifie que mon `hosts.ini` et mes `group_vars/` sont **bien structurés** : Ansible arrive
à les lire, les groupes sont bons, et chaque machine a les bonnes variables. **Aucune VM requise**,
car on ne fait que *lire* l'inventaire, on ne se connecte à rien.

### 4.1 Aller dans le dossier ansible
```bash
cd /mnt/c/Users/jamai/OneDrive/Desktop/shellter-push/ansible
```
**Pourquoi `/mnt/c/...`** : depuis Ubuntu, le disque `C:` de Windows est monté sous `/mnt/c`. C'est
le même dossier que dans l'explorateur Windows, vu depuis Linux.

### 4.2 Afficher la structure de l'inventaire
```bash
ansible-inventory -i hosts.ini --graph
```
**Ce que ça fait** : dessine l'arbre des groupes et des machines lus dans `hosts.ini`.
**Résultat attendu** :
```
@all:
  |--@ungrouped:
  |--@shellter:
  |  |--@controller:
  |  |  |--controller
  |  |--@workers:
  |  |  |--worker1
  |  |  |--worker2
  |  |  |--worker3
```
✅ Si tu vois les groupes `controller` et `workers` avec les 4 machines, **la structure est bonne**.

### 4.3 Vérifier les variables d'une machine
```bash
ansible-inventory -i hosts.ini --host worker1
```
**Ce que ça fait** : affiche toutes les variables qu'Ansible associe à `worker1` (celles de
`group_vars/all/` + celles de `group_vars/workers.yml`).
**Résultat attendu** (extrait) :
```json
{
    "ansible_host": "192.168.56.11",
    "ansible_user": "vagrant",
    "agent_port": 5000,
    "worker_max_instances": 10,
    "ssh_port_range_start": 20000,
    "ssh_port_range_end": 30000
}
```
✅ La bonne IP (`.11` pour worker1, `.12` pour worker2, `.13` pour worker3) et les variables
attendues → **les group_vars sont bien pris en compte**. Refais-le avec `worker2` et `worker3`.

### 4.4 Vérifier que le script réseau est correct
```bash
bash -n ../scripts/check_network.sh && echo "script OK"
```
**Ce que ça fait** : `bash -n` lit le script **sans l'exécuter** et signale toute erreur de syntaxe.
✅ Affiche `script OK` = le script est syntaxiquement valide.

---

## 5. Les 2 warnings que tu vas voir (et pourquoi ils sont normaux)

### ⚠️ « Ansible is being run in a world writable directory … ignoring ansible.cfg »
**Cause** : on travaille sur `/mnt/c` (disque Windows). Pour Linux, ce dossier est « accessible en
écriture par tout le monde », et par **sécurité** Ansible refuse d'y lire le `ansible.cfg` (un cfg
malveillant pourrait exécuter n'importe quoi). Ce n'est **pas** une erreur de mon travail.

**Comment l'éviter** (optionnel) — copier le projet dans le système de fichiers Linux :
```bash
cp -r /mnt/c/Users/jamai/OneDrive/Desktop/shellter-push ~/shellter
cd ~/shellter/ansible
ansible-inventory --graph     # ici, plus besoin de -i, le ansible.cfg est lu
```
> C'est aussi **plus rapide** : Ansible sur `/mnt/c` est lent (accès disque Windows depuis Linux).

### ⚠️ « Found both group and host with same name: controller »
**Cause** : le **groupe** s'appelle `[controller]` et la **machine** aussi `controller`. Ansible le
signale mais ça fonctionne (on garde ce nom car c'est celui du sujet de la prof, page 9). Bénin.

---

## 6. Niveau 2 — Le vrai test avec les VM (quand l'infra tourne)

Ce niveau nécessite que le `Vagrantfile` de l'équipe existe et que les VM démarrent. C'est la
**preuve finale** de la S2.

```bash
# à la racine du dépôt (côté Windows ou WSL selon où tourne Vagrant)
vagrant up            # démarre les 4 VM
vagrant status        # doit montrer 4 VM "running"

cd ansible
ansible all -m ping   # 🎯 LA PREUVE : chaque machine répond "pong" (SUCCESS)

bash ../scripts/check_network.sh   # ping + SSH entre toutes les VM -> tout OK
```
**Pourquoi `ansible all -m ping`** : le module `ping` d'Ansible se connecte en SSH à chaque machine
et vérifie que Python y répond. Si les 4 répondent `SUCCESS`, ça prouve que l'inventaire **et** la
connexion SSH fonctionnent → objectif S2 atteint.

> ⚠️ **Prérequis à rappeler à l'équipe** : le `Vagrantfile` doit contenir
> `config.ssh.insert_key = false`, sinon chaque VM a une clé SSH différente et l'inventaire ne peut
> pas toutes les joindre avec une seule clé.
>
> ⚠️ **Réseau WSL** : WSL2 est sur un réseau NAT ; joindre des VM VirtualBox/VMware en
> `192.168.56.x` depuis WSL peut échouer. Dans ce cas, lancer `ansible all -m ping` **depuis la VM
> controller** (`vagrant ssh controller`) plutôt que depuis WSL.

---

## 7. Récapitulatif (checklist)

| Test | Commande | VM requises ? | Preuve |
|---|---|---|---|
| Structure de l'inventaire | `ansible-inventory -i hosts.ini --graph` | ❌ | 2 groupes + 4 machines |
| Variables d'un hôte | `ansible-inventory -i hosts.ini --host worker1` | ❌ | bonne IP + variables |
| Syntaxe du script | `bash -n ../scripts/check_network.sh` | ❌ | `script OK` |
| **Connexion réelle** | `ansible all -m ping` | ✅ | `SUCCESS` × 4 |
| Réseau inter-VM | `bash ../scripts/check_network.sh` | ✅ | tout en `OK` |

**Aujourd'hui, sans VM**, les 3 premiers tests suffisent à prouver que mon rendu S2 est correct.
Les 2 derniers se valideront en séance, une fois l'infrastructure Vagrant en place.
