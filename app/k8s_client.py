"""Client Kubernetes — remplace le Worker Agent (branche kubernetes, séances K3/K4).

Au lieu d'appeler l'API d'un Worker Agent, Flask parle directement à l'API Kubernetes :
chaque location devient un **Deployment (1 replica)** + un **Service NodePort** (port 22).
Le Deployment (et non un Pod nu) donne la reprise sur panne NATIVE : si le pod ou son
nœud tombe, Kubernetes le recrée tout seul.

Interface volontairement calquée sur agent_client (create/delete) pour que l'adaptation
de /rent soit minimale.
"""
import os
import time

from kubernetes import client, config
from kubernetes.client.rest import ApiException

NAMESPACE = os.getenv("SHELLTER_NAMESPACE", "shellter")
# IP de repli si le nœud du pod n'est pas encore connu (NodePort est joignable sur
# tous les nœuds, donc n'importe quelle IP de nœud fonctionne).
DEFAULT_NODE_IP = os.getenv("NODE_IP_FALLBACK", "192.168.56.10")
SCHEDULE_TIMEOUT = int(os.getenv("K8S_SCHEDULE_TIMEOUT", "30"))


class K8sError(Exception):
    """Échec d'appel à l'API Kubernetes (équivalent d'AgentError)."""


def _load():
    """Charge la config in-cluster (dans un pod) ou locale (poste de dev)."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config(config_file=os.getenv("KUBECONFIG"))


_load()
_apps = client.AppsV1Api()
_core = client.CoreV1Api()


def _deployment_manifest(instance_id, image, ssh_user, ssh_secret, expires_at):
    name = f"env-{instance_id}"
    # Labels : seulement des valeurs VALIDES (alphanum, '-', '_', '.').
    labels = {
        "app": "shellter-env",
        "shellter.instance_id": str(instance_id),
    }
    # expires_at est une date ISO (contient ':' et '+') -> INTERDIT en label.
    # On la met en ANNOTATION (qui accepte n'importe quelle valeur).
    annotations = {"shellter.expires_at": expires_at or ""}
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name, "namespace": NAMESPACE,
            "labels": labels, "annotations": annotations,
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"shellter.instance_id": str(instance_id)}},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": [{
                        "name": "ssh",
                        "image": image,
                        "ports": [{"containerPort": 22}],
                        "env": [
                            {"name": "SSH_USER", "value": ssh_user},
                            {"name": "SSH_PASSWORD", "value": ssh_secret},
                        ],
                    }],
                },
            },
        },
    }


def _service_manifest(instance_id):
    name = f"env-{instance_id}"
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": NAMESPACE,
            "labels": {"app": "shellter-env", "shellter.instance_id": str(instance_id)},
        },
        "spec": {
            "type": "NodePort",
            "selector": {"shellter.instance_id": str(instance_id)},
            # nodePort non spécifié -> Kubernetes en alloue un libre (30000-32767).
            "ports": [{"port": 22, "targetPort": 22}],
        },
    }


def _node_ip_for_instance(instance_id):
    """IP d'un nœud joignable pour l'instance (celui qui héberge le pod si connu)."""
    try:
        pods = _core.list_namespaced_pod(
            NAMESPACE, label_selector=f"shellter.instance_id={instance_id}")
        for pod in pods.items:
            node_name = pod.spec.node_name
            if node_name:
                node = _core.read_node(node_name)
                for addr in node.status.addresses:
                    if addr.type == "InternalIP":
                        return addr.address
    except ApiException:
        pass
    return DEFAULT_NODE_IP


def create_env(image, instance_id, ssh_user, ssh_secret, expires_at=""):
    """Crée la location : Deployment + Service NodePort. Retourne pod/nodeport/node_ip."""
    try:
        _apps.create_namespaced_deployment(
            NAMESPACE, body=_deployment_manifest(
                instance_id, image, ssh_user, ssh_secret, expires_at))
        svc = _core.create_namespaced_service(
            NAMESPACE, body=_service_manifest(instance_id))
    except ApiException as exc:
        # nettoyage best-effort pour ne pas laisser d'orphelin
        delete_env(instance_id)
        raise K8sError(f"création de l'environnement échouée : {exc.reason}") from exc

    nodeport = svc.spec.ports[0].node_port

    # attendre que le pod soit schedulé (nodeName attribué) pour connaître l'IP du nœud
    node_ip = DEFAULT_NODE_IP
    deadline = time.time() + SCHEDULE_TIMEOUT
    while time.time() < deadline:
        ip = _node_ip_for_instance(instance_id)
        if ip != DEFAULT_NODE_IP:
            node_ip = ip
            break
        time.sleep(1)

    return {
        "deployment": f"env-{instance_id}",
        "nodeport": nodeport,
        "node_ip": node_ip,
        "container_id": f"env-{instance_id}",   # compat avec le schéma existant
    }


def delete_env(instance_id):
    """Supprime la location (Deployment + Service). Idempotent."""
    name = f"env-{instance_id}"
    for fn, kind in ((_apps.delete_namespaced_deployment, "deployment"),
                     (_core.delete_namespaced_service, "service")):
        try:
            fn(name=name, namespace=NAMESPACE)
        except ApiException as exc:
            if exc.status != 404:   # 404 = déjà supprimé -> on ignore
                raise K8sError(f"suppression {kind} échouée : {exc.reason}") from exc


def list_envs():
    """Liste les locations actives dans le cluster (pour la réconciliation, K4)."""
    deps = _apps.list_namespaced_deployment(
        NAMESPACE, label_selector="app=shellter-env")
    return [{
        "instance_id": d.metadata.labels.get("shellter.instance_id"),
        "expires_at": (d.metadata.annotations or {}).get("shellter.expires_at"),
        "ready": (d.status.ready_replicas or 0) >= 1,
    } for d in deps.items]
