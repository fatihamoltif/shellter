# 📘 Documentation S6 : Déploiement de l'Agent Worker (Rôle P2)

Cette section détaille la mise en place de la télémétrie et de l'auto-enregistrement des nœuds workers auprès du contrôleur principal de l'infrastructure Shellter.

## 1. Architecture et Auto-enregistrement

L'architecture repose sur un modèle d'auto-découverte dynamique push-based :
- **L'Agent (Worker)** : Un script Python (`agent.py`) s'exécute de manière autonome sur chaque nœud worker. Il est chargé de collecter la télémétrie de la machine (hostname, adresses IP, charge CPU, consommation RAM) ainsi que l'état du démon Docker.
- **Le Contrôleur (API Flask)** : L'application centrale expose le point de terminaison `POST /workers/register`. Cette route est sécurisée par la variable d'environnement `AGENT_TOKEN`.
- **Le Flux** : Au démarrage, puis à intervalles réguliers, l'agent envoie sa télémétrie au contrôleur via une requête HTTP. Le contrôleur enregistre ou met à jour les informations de la machine en base de données. Une route `GET /workers/` permet ensuite de lister l'ensemble des workers et leur état.

## 2. Lancement du Déploiement

Le déploiement des agents est entièrement automatisé via Ansible. Le playbook `worker.yml` se charge d'installer l'environnement Python requis, de copier le script de l'agent sur les 3 nœuds workers, et de créer un service `systemd` (`shellter-agent.service`). Ce service garantit l'exécution de l'agent en tâche de fond, avec une injection dynamique des configurations (comme les adresses IP).

Pour lancer le déploiement sur les workers, exécutez la commande suivante depuis la racine du projet :

```bash
ansible-playbook -i ansible/hosts.ini ansible/worker.yml --ask-vault-pass
```

## 3. Vérification du Succès

Une fois le playbook terminé avec succès (sans tâches en statut *failed*), les services `systemd` démarreront automatiquement sur les workers et commenceront à "ping" le contrôleur.

Pour valider le bon fonctionnement de l'auto-enregistrement, interrogez l'API du contrôleur (assurez-vous que l'application web tourne localement ou sur votre serveur) :

```bash
curl http://localhost:5000/workers/
```

**Résultat attendu :**
La commande doit retourner un tableau JSON listant les différents workers. Pour que le test soit considéré comme validé, vous devez vérifier que le statut des workers remonte bien en `"AVAILABLE"` :

```json
[
  {
    "id": 1,
    "hostname": "worker-01",
    "ip": "10.0.0.X",
    "status": "AVAILABLE",
    "cpu": 15.4,
    "memory": 42.8
  }
]
```
