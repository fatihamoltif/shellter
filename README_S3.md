# 🚀 Documentation S3 : Installation de Docker via Ansible

## 📖 Contexte du Projet
**Équipe Shellter** : Youssef, Noah, Aziz et Isselmou.

Notre infrastructure repose sur **4 machines virtuelles Ubuntu** (1 Controller, 3 Workers) provisionnées avec Vagrant sous Windows. Toute notre automatisation logicielle (configuration et déploiement) est gérée depuis **WSL2 (Ubuntu)** avec Ansible.

## 🎯 Objectif du Document
Ce guide explique pas à pas comment monter l'infrastructure et exécuter notre playbook Ansible pour installer Docker. Il permet de contourner les pièges classiques liés au routage réseau et à l'authentification SSH entre l'environnement Windows et WSL2.

---

## ⚙️ 1. Prérequis Matériel

⚠️ **Choix du Provider** : Il est strictement obligatoire d'utiliser le provider **VirtualBox** pour Vagrant. L'utilisation de VMware pose des soucis de routage insolubles avec WSL2 dans notre configuration actuelle.

💡 **Vérification Réseau** : Assurez-vous sous Windows (via le Panneau de configuration ou les Paramètres Réseau) que la carte réseau **"VirtualBox Host-Only Ethernet"** est bien activée et fonctionnelle.

---

## 🏗️ 2. Démarrage de l'Infrastructure (PowerShell)

Depuis un terminal **PowerShell** sous Windows, placez-vous à la racine du projet Shellter (là où se trouve le `Vagrantfile`) et lancez les machines :

```powershell
vagrant up
```

Cette commande initialise nos 4 machines virtuelles et leur attribue automatiquement des adresses IP statiques dans le sous-réseau `192.168.56.x`.

---

## 🔑 3. Préparation de l'Authentification (Terminal WSL)

⚠️ **Étape Critique !** Ansible tournant sous WSL2 a besoin d'une clé SSH pour se connecter aux VMs Windows. Les permissions de fichiers entre Windows (NTFS) et WSL (ext4) étant différentes, il faut rapatrier la clé privée avec les bons droits de sécurité, sinon Ansible refusera de s'en servir.

Ouvrez votre terminal **WSL (Ubuntu)** et exécutez ces commandes en remplaçant `<Ton_User_Windows>` par votre nom d'utilisateur Windows :

```bash
# 1. Création du dossier Vagrant caché dans votre /home WSL
mkdir -p ~/.vagrant.d

# 2. Copie de la clé privée par défaut de Vagrant depuis Windows vers WSL
cp /mnt/c/Users/<Ton_User_Windows>/.vagrant.d/insecure_private_key ~/.vagrant.d/

# 3. Restriction des droits (sécurité SSH obligatoire)
chmod 600 ~/.vagrant.d/insecure_private_key
```

---

## 🚀 4. Déploiement Ansible (Terminal WSL)

Toujours depuis votre terminal **WSL**, placez-vous dans le répertoire du projet (ex: `/mnt/c/Users/<Ton_User_Windows>/projet_shelter/`) et lancez le déploiement.

💡 **Astuce** : La désactivation de la vérification des clés hôtes (`ANSIBLE_HOST_KEY_CHECKING=False`) est indispensable, car nous recréons souvent nos VMs Vagrant, ce qui modifie leurs empreintes SSH et bloquerait Ansible.

```bash
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i ansible/hosts.ini ansible/docker.yml -u vagrant --private-key ~/.vagrant.d/insecure_private_key --ask-vault-pass
```
*(Le mot de passe Vault vous sera demandé pour décrypter d'éventuelles variables sensibles).*

---

## ✅ 5. Preuve de Validation (PowerShell)

Pour s'assurer que Docker a bien été déployé sur notre infrastructure, retournez sur **PowerShell** :

1. Connectez-vous à la machine "control" :
   ```powershell
   vagrant ssh control
   ```
2. Lancez le conteneur de test Docker :
   ```bash
   sudo docker run hello-world
   ```

Si le message **"Hello from Docker!"** s'affiche, le déploiement est un succès ! 🎉

---

## 💡 6. Prochaines Étapes (Amélioration Continue)

Actuellement, l'exécution des commandes Docker nécessite `sudo`.
Pour optimiser notre confort de travail et l'exécution de futurs scripts automatisés, il est fortement recommandé d'ajouter une nouvelle tâche dans notre playbook `ansible/docker.yml`.

**Tâche à ajouter pour éviter le sudo :** Intégrer automatiquement l'utilisateur `vagrant` au groupe `docker`.
