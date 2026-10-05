from flask import request, jsonify, current_app
from app.models import db, Worker, Instance
from datetime import datetime, timezone

from . import bp

def check_agent_token(req):
    """Vérifie que la requête contient le bon token d'authentification de l'agent."""
    auth_header = req.headers.get('Authorization')
    expected_token = current_app.config.get('AGENT_TOKEN')
    
    if not auth_header or auth_header != f"Bearer {expected_token}":
        return False
    return True

@bp.route('/register', methods=['POST'])
def register_worker():
    """Route appelée par l'agent pour s'enregistrer au démarrage."""
    if not check_agent_token(request):
        return jsonify({'error': 'Accès non autorisé : Token invalide ou manquant'}), 401
    
    data = request.get_json()
    hostname = data.get('hostname')
    
    if not hostname:
        return jsonify({'error': 'Le champ hostname est obligatoire'}), 400

    # Recherche si le worker existe déjà pour le mettre à jour, sinon on le crée
    worker = Worker.query.filter_by(hostname=hostname).first()
    
    if worker:
        worker.ip = data.get('ip', worker.ip)
        worker.cpu = data.get('cpu', worker.cpu)
        worker.memory = data.get('memory', worker.memory)
        worker.status = 'AVAILABLE'
        worker.last_heartbeat = datetime.now(timezone.utc)
    else:
        worker = Worker(
            hostname=hostname,
            ip=data.get('ip'),
            cpu=data.get('cpu'),
            memory=data.get('memory'),
            status='AVAILABLE',
            last_heartbeat=datetime.now(timezone.utc)
        )
        db.session.add(worker)
        
    db.session.commit()
    return jsonify({'message': 'Worker enregistré avec succès', 'worker_id': worker.id}), 200

@bp.route('/', methods=['GET'])
def get_workers():
    """Retourne la liste de tous les workers."""
    # L'accès à cette route dépend de votre implémentation (admin ou token),
    # tu peux ajouter check_agent_token(request) si nécessaire.
    workers = Worker.query.all()
    return jsonify([{
        'id': w.id, 
        'hostname': w.hostname, 
        'ip': w.ip, 
        'status': w.status, 
        'cpu': w.cpu, 
        'memory': w.memory
    } for w in workers]), 200

@bp.route('/<int:id>', methods=['GET'])
def get_worker(id):
    """Retourne les détails d'un worker spécifique."""
    worker = Worker.query.get_or_404(id)
    return jsonify({
        'id': worker.id, 
        'hostname': worker.hostname, 
        'ip': worker.ip, 
        'status': worker.status, 
        'cpu': worker.cpu, 
        'memory': worker.memory
    }), 200

@bp.route('/instances/<container_name>/update_port', methods=['POST'])
def update_instance_port(container_name):
    # Sécuriser la route (vérification du token)
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {current_app.config['AGENT_TOKEN']}":
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    new_port = data.get('new_port')
    
    # Mettre à jour la base de données
    instance = Instance.query.filter_by(container_name=container_name).first()
    if instance:
        instance.ssh_port = new_port
        db.session.commit()
        # Optionnel : logguer un message spécifique pour qu'il s'affiche sur le dashboard
        return jsonify({"message": "Port mis à jour avec succès", "new_port": new_port}), 200
        
    return jsonify({"error": "Instance introuvable"}), 404