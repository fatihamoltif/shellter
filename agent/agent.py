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

if __name__ == '__main__':
    # Au démarrage du service, on s'enregistre
    register_to_controller()
    
    # On maintient le script en vie (P1 rajoutera le heartbeat ici en S7)
    while True:
        time.sleep(10)