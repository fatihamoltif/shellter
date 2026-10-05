"""Worker Agent simulé pour les tests d'intégration.

Il répond aux appels HTTP de Flask sans créer de vrai conteneur Docker.
"""

from flask import Flask, jsonify


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        status="ok"
    ), 200


@app.post("/containers")
def create_container():
    return jsonify(
        container_id="mock-container-001",
        status="running",
    ), 201


@app.delete("/containers/<container_id>")
def delete_container(container_id):
    return "", 204


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )