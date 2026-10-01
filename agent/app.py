import uuid

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from flask import Flask, jsonify, request


app = Flask(__name__)
docker_client = docker.from_env()


@app.get("/containers")
def list_containers():
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
    data = request.get_json(silent=True) or {}

    instance_id = data.get("instance_id")
    image = data.get("image")
    expires_at = data.get("expires_at")

    cpu = data.get("cpu", 1)
    memory = data.get("memory", "512m")
    environment = data.get("environment", {})

    if not instance_id or not image or not expires_at:
        return (
            jsonify(
                {
                    "error": (
                        "instance_id, image et expires_at "
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

        labels = {
            "shellter.instance_id": str(instance_id),
            "shellter.expires_at": str(expires_at),
        }
        nano_cpus = int(float(cpu) * 1_000_000_000)
        container = docker_client.containers.create(
            image=image,
            name=container_name,
            detach=True,
            labels=labels,
            environment=environment,
            nano_cpus=nano_cpus,
            mem_limit=memory,
            ports={"22/tcp": None},
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

        ssh_port = int(port_info[0]["HostPort"])

        return (
            jsonify(
                {
                    "container_id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "ssh_port": ssh_port,
                }
            ),
            201,
        )

    except ImageNotFound:
        if container is not None:
            container.remove(force=True)

        return jsonify({"error": "Image Docker introuvable"}), 400

    except (DockerException, RuntimeError, ValueError) as exc:
        # Très important :
        # on ne laisse pas de conteneur orphelin.
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                pass

        return jsonify({"error": str(exc)}), 500


@app.delete("/containers/<container_id>")
def delete_container(container_id):
    """
    Supprime un conteneur Shellter.
    """
    try:
        container = docker_client.containers.get(container_id)

        # Protection : on évite de supprimer un conteneur
        # qui n'appartient pas à Shellter.
        if not container.labels.get("shellter.instance_id"):
            return (
                jsonify(
                    {"error": "Ce conteneur n'appartient pas à Shellter"}
                ),
                403,
            )

        container.remove(force=True)

        return jsonify({"status": "deleted"}), 200

    except NotFound:
        return jsonify({"error": "Conteneur introuvable"}), 404

    except DockerException as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/health")
def health():
    """
    Vérifie que l'agent arrive à parler à Docker.
    """
    try:
        docker_client.ping()
        return jsonify({"status": "ok"}), 200
    except DockerException:
        return jsonify({"status": "docker_unavailable"}), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False,
    )