"""Worker Agent RÉEL — lance de vrais conteneurs SSH via le SDK Docker.

Reçoit les appels de Flask (POST/DELETE /containers) et crée/détruit des conteneurs
frères sur le démon Docker de l'hôte (socket monté). Chaque conteneur est une distro
avec sshd, son port 22 publié sur un port de l'hôte.
"""
import os

import docker
from flask import Flask, jsonify, request

app = Flask(__name__)
client = docker.from_env()

SSH_DIR = os.getenv("SSH_IMAGE_DIR", "/agent/ssh")
_built = set()


def ensure_image(base_image):
    """Construit (si besoin) l'image SSH pour la distro demandée et renvoie son tag."""
    tag = "shellter-ssh:" + base_image.replace(":", "-").replace("/", "-")
    if tag in _built:
        return tag
    try:
        client.images.get(tag)
    except docker.errors.ImageNotFound:
        client.images.build(path=SSH_DIR, buildargs={"BASE": base_image}, tag=tag, rm=True)
    _built.add(tag)
    return tag


@app.post("/containers")
def create_container():
    data = request.get_json(force=True)
    base = data["image"]
    port = int(data["ssh_port"])
    labels = {k: str(v) for k, v in data.get("labels", {}).items()}
    instance_id = labels.get("shellter.instance_id", "x")

    tag = ensure_image(base)
    name = f"shellter-env-{instance_id}-{port}"

    # nettoyer un éventuel conteneur de même nom
    try:
        client.containers.get(name).remove(force=True)
    except docker.errors.NotFound:
        pass

    container = client.containers.run(
        tag,
        detach=True,
        name=name,
        hostname=f"env-{instance_id}",
        ports={"22/tcp": port},                 # 22 du conteneur -> port de l'hôte
        environment={
            "SSH_USER": data.get("ssh_user", "shellter"),
            "SSH_PASSWORD": data.get("ssh_secret", "changeme"),
        },
        labels=labels,
    )
    return jsonify(container_id=container.id[:12], status="running"), 201


@app.delete("/containers/<cid>")
def delete_container(cid):
    try:
        client.containers.get(cid).remove(force=True)
    except docker.errors.NotFound:
        pass
    return "", 204


@app.get("/containers")
def list_containers():
    cs = client.containers.list(filters={"label": "shellter.instance_id"})
    return jsonify([{"id": c.id[:12], "name": c.name, "status": c.status} for c in cs]), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
