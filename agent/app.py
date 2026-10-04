import uuid

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from flask import Flask, jsonify, request


app = Flask(__name__)
docker_client = docker.from_env()


@app.get("/containers")
def list_containers():
    """Liste uniquement les conteneurs créés par Shellter."""

    try:
        containers = docker_client.containers.list(
            all=True,
            filters={"label": "shellter.instance_id"},
        )

        result = []

        for container in containers:
            result.append(
                {
                    "container_id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "instance_id": container.labels.get(
                        "shellter.instance_id"
                    ),
                    "expires_at": container.labels.get(
                        "shellter.expires_at"
                    ),
                }
            )

        return jsonify(result), 200

    except DockerException as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/containers")
def create_container():
    """Crée et démarre un conteneur Shellter."""

    data = request.get_json(silent=True) or {}

    image = data.get("image")

    # P4 envoie les informations Shellter dans "labels".
    labels = data.get("labels", {})

    # Compatibilité avec nos anciens tests S6 :
    # on accepte aussi instance_id / expires_at directement.
    instance_id = (
        data.get("instance_id")
        or labels.get("shellter.instance_id")
    )

    expires_at = (
        data.get("expires_at")
        or labels.get("shellter.expires_at")
    )

    # P4 choisit le port SSH avant d'appeler l'agent.
    ssh_port = data.get("ssh_port")

    # Credentials générés côté Flask.
    ssh_user = data.get("ssh_user")
    ssh_secret = data.get("ssh_secret")

    # Valeurs par défaut pour les ressources.
    cpu = data.get("cpu", 1)
    memory = data.get("memory", "512m")

    # Compatibilité avec l'ancien format de test.
    environment = data.get("environment", {})

    if ssh_user:
        environment["SSH_USER"] = ssh_user

    if ssh_secret:
        environment["SSH_PASSWORD"] = ssh_secret

    if not instance_id or not image or not expires_at:
        return (
            jsonify(
                {
                    "error": (
                        "image, instance_id et expires_at "
                        "sont obligatoires"
                    )
                }
            ),
            400,
        )

    if (
        "SSH_USER" not in environment
        or "SSH_PASSWORD" not in environment
    ):
        return (
            jsonify(
                {
                    "error": (
                        "SSH_USER et SSH_PASSWORD "
                        "sont obligatoires"
                    )
                }
            ),
            400,
        )

    container = None

    try:
        container_name = (
            f"shellter-{instance_id}-{uuid.uuid4().hex[:8]}"
        )

        shellter_labels = {
            "shellter.instance_id": str(instance_id),
            "shellter.expires_at": str(expires_at),
        }

        nano_cpus = int(float(cpu) * 1_000_000_000)

        # Si P4 a choisi un port, on l'utilise.
        # Sinon Docker peut en choisir un automatiquement
        # pour les anciens tests directs.
        published_port = (
            int(ssh_port)
            if ssh_port is not None
            else None
        )

        container = docker_client.containers.create(
            image=image,
            name=container_name,
            detach=True,
            labels=shellter_labels,
            environment=environment,
            nano_cpus=nano_cpus,
            mem_limit=memory,
            ports={"22/tcp": published_port},
        )

        container.start()
        container.reload()

        port_info = container.attrs[
            "NetworkSettings"
        ]["Ports"].get("22/tcp")

        if not port_info:
            raise RuntimeError(
                "Docker n'a pas attribué de port SSH"
            )

        real_ssh_port = int(port_info[0]["HostPort"])

        return (
            jsonify(
                {
                    "container_id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "ssh_port": real_ssh_port,
                }
            ),
            201,
        )

    except ImageNotFound:
        if container is not None:
            container.remove(force=True)

        return (
            jsonify({"error": "Image Docker introuvable"}),
            400,
        )

    except (DockerException, RuntimeError, ValueError) as exc:
        # Si la création a commencé mais échoue ensuite,
        # on supprime le conteneur pour éviter un orphelin.
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                pass

        return jsonify({"error": str(exc)}), 500


@app.delete("/containers/<container_id>")
def delete_container(container_id):
    """Supprime un conteneur Shellter."""

    try:
        container = docker_client.containers.get(container_id)

        # Empêche l'agent de supprimer un conteneur
        # qui n'appartient pas à Shellter.
        if not container.labels.get("shellter.instance_id"):
            return (
                jsonify(
                    {
                        "error": (
                            "Ce conteneur n'appartient pas "
                            "à Shellter"
                        )
                    }
                ),
                403,
            )

        container.remove(force=True)

        return jsonify({"status": "deleted"}), 200

    except NotFound:
        # Pour S7, le client considérera ce 404
        # comme "déjà supprimé".
        return (
            jsonify({"error": "Conteneur introuvable"}),
            404,
        )

    except DockerException as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/health")
def health():
    """Vérifie que l'agent peut communiquer avec Docker."""

    try:
        docker_client.ping()
        return jsonify({"status": "ok"}), 200

    except DockerException:
        return jsonify(
            {"status": "docker_unavailable"}
        ), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )