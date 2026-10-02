# 📘 Documentation S7 : Auto-guérison et Watcher (Rôle P2)

Cette section détaille la mise en place de la résilience de notre infrastructure à travers un mécanisme d'auto-guérison (self-healing) piloté par nos workers.

## 1. Architecture d'Auto-guérison (Le Watcher)

Notre infrastructure est désormais capable de survivre au crash inattendu d'un environnement utilisateur grâce aux mécanismes suivants :

- **Surveillance Active (Polling)** : L'agent Python (`agent.py`) intègre un Watcher. Une boucle infinie interroge l'API du démon Docker local toutes les 15 secondes pour vérifier l'état de tous les conteneurs liés à notre infrastructure (filtrés via le label `shellter`).
- **Résurrection (Auto-healing)** : Si le Watcher détecte qu'un conteneur est à l'état `exited` (suite à une erreur, un OOM kill ou un arrêt forcé), il déclenche instantanément la commande de redémarrage (`container.start()`).
- **Mise à jour du Port Dynamique** : Docker réattribue un nouveau port hôte dynamique lors du redémarrage d'un conteneur. Le Watcher lit les nouvelles métadonnées réseau du conteneur et extrait le nouveau port mappé sur le `22/tcp`. 
- **Synchronisation avec le Contrôleur** : L'agent envoie une requête `POST /instances/<nom>/update_port` sécurisée avec `AGENT_TOKEN` au contrôleur. Cela permet à la base de données centrale d'être mise à jour, garantissant que l'utilisateur final pourra toujours se connecter en SSH sans intervention manuelle.
- **Observabilité** : Le service `systemd` exécute désormais Python avec le flag `-u` (unbuffered). Cela désactive la mise en cache de la sortie standard, permettant une lecture immédiate et fluide des logs d'alerte dans le journal système.

## 2. Comment tester la résilience

Pour tester l'auto-guérison en conditions réelles, connectez-vous en SSH sur l'un de vos nœuds workers (ex: `shellter-worker-1`) qui héberge actuellement un ou plusieurs conteneurs, et suivez cette procédure :

**Étape 1 : Observer les logs du Watcher**
Dans un premier terminal, lancez le suivi des logs de l'agent en temps réel :
```bash
sudo journalctl -u shellter-agent.service -f
```

**Étape 2 : Simuler une panne**
Ouvrez un second terminal sur le même worker et "tuez" violemment un conteneur en cours d'exécution :
```bash
# Pour lister les conteneurs et trouver un nom :
sudo docker ps

# Pour tuer le conteneur :
sudo docker kill <nom_du_conteneur>
```

**Étape 3 : Vérifier la résurrection**
Regardez immédiatement votre premier terminal. En moins de 15 secondes, vous verrez apparaître les logs de détection et de réparation :
1. `[ALERTE] Conteneur <nom> (mort) détecté. Tentative de relance...`
2. `[RECOVERY] <nom> relancé sur le port <nouveau_port>. Notification de l'API...`

Côté API du contrôleur, la route `update_port` aura reçu l'alerte et mis à jour le port dans la base de données. L'utilisateur peut se reconnecter !
