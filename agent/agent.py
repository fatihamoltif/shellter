import os
import socket
import psutil
import requests
import docker
import time

# Ces variables seront injectées par Ansible via systemd
CONTROLLER_URL = os.getenv('CONTROLLER_URL', 'http://192.168.56.10:5000')
AGENT_TOKEN = os.getenv('AGENT_TOKEN')
# L'IP est souvent difficile à deviner s'il y a plusieurs interfaces réseau,
# il est plus propre de la faire passer par Ansible.
WORKER_IP = os.getenv('WORKER_IP')

def get_system_info():
    """Récupère les ressources matérielles du worker."""
    hostname = socket.gethostname()
    cpu_count = psutil.cpu_count(logical=True)
    # Convertir la RAM de bytes en Gigaoctets
    memory_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    
    return {
        "hostname": hostname,
        "ip": WORKER_IP,
        "cpu": cpu_count,
        "memory": memory_gb
    }

def register_to_controller():
    """Vérifie Docker et envoie les infos à l'API Flask."""
    try:
        # 1. Vérification de l'état de Docker
        client = docker.from_env()
        client.ping()
        print("Docker est actif.")
    except Exception as e:
        print(f"Erreur : Impossible de joindre le démon Docker. {e}")
        return False

    # 2. Récupération des infos système
    info = get_system_info()
    headers = {'Authorization': f'Bearer {AGENT_TOKEN}'}
    
    # 3. Appel POST vers le controller
    print(f"Tentative d'enregistrement auprès de {CONTROLLER_URL}...")
    try:
        response = requests.post(f"{CONTROLLER_URL}/workers/register", json=info, headers=headers, timeout=5)
        response.raise_for_status()
        print(f"Succès ! Worker enregistré : {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Échec de l'enregistrement : {e}")
        return False

def watch_containers():
    # 1. On initialise le client Docker ICI
    docker_client = docker.from_env()
    
    # On filtre uniquement les conteneurs créés par notre infrastructure
    containers = docker_client.containers.list(all=True, filters={"label": "shellter"})
    
    for container in containers:
        if container.status == 'exited':
            print(f"[ALERTE] Conteneur {container.name} (mort) détecté. Tentative de relance...")
            try:
                # 1. Redémarrer le conteneur
                container.start()
                
                # 2. Recharger les métadonnées pour lire le nouveau port dynamique
                container.reload()
                ports = container.attrs['NetworkSettings']['Ports']
                new_ssh_port = ports['22/tcp'][0]['HostPort']
                
                print(f"[RECOVERY] {container.name} relancé sur le port {new_ssh_port}. Notification de l'API...")
                
                # 3. Prévenir l'API Flask du changement de port
                headers = {"Authorization": f"Bearer {AGENT_TOKEN}"}
                payload = {"new_port": new_ssh_port}
                
                # On suppose que l'API a une route pour mettre à jour l'instance par son nom ou son ID
                requests.post(f"{CONTROLLER_URL}/instances/{container.name}/update_port", 
                              json=payload, headers=headers)
                              
            except Exception as e:
                print(f"[ERREUR] Impossible de recréer {container.name}: {e}")

if __name__ == '__main__':
    # Au démarrage du service, on s'enregistre
    register_to_controller()
    
    # On lance la boucle unique qui fait office de Watcher (et de Heartbeat)
    print("Démarrage du Watcher...")
    while True:
        watch_containers()
        time.sleep(15) # Vérification toutes les 15 secondes