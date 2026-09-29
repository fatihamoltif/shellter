"""Client vers l'API du Worker Agent — Séance S6.

Flask ne parle jamais directement au démon Docker : il appelle l'API de l'agent du worker.
Ce module est la « couture » : P3 fournira l'agent réel ; ici on a un client HTTP simple,
facilement remplaçable (mocké dans les tests).
"""
import requests


class AgentError(Exception):
    """Échec d'appel à l'agent (réseau, timeout, réponse invalide)."""


def create_container(worker, image, ssh_port, instance_id, ssh_user, ssh_secret, expires_at):
    """Demande à l'agent de créer un conteneur. Retourne un dict {container_id, ...}."""
    try:
        resp = requests.post(
            f"{worker.agent_url}/containers",
            json={
                "image": image,
                "ssh_port": ssh_port,
                "ssh_user": ssh_user,
                "ssh_secret": ssh_secret,
                "labels": {
                    "shellter.instance_id": str(instance_id),
                    "shellter.expires_at": expires_at,
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise AgentError(str(exc)) from exc


def delete_container(worker, container_id):
    """Demande à l'agent de détruire un conteneur. Idempotent côté agent."""
    try:
        resp = requests.delete(
            f"{worker.agent_url}/containers/{container_id}",
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise AgentError(str(exc)) from exc
