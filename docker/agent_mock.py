"""Agent mock pour les tests d'intégration (S8).

Simule l'API du Worker Agent (que P3 implémentera réellement) : répond à la création
et à la suppression de conteneurs, sans lancer de vrai Docker.
"""
from flask import Flask, jsonify

app = Flask(__name__)


@app.post("/containers")
def create_container():
    return jsonify(container_id="mock-container-001", status="running"), 201


@app.delete("/containers/<cid>")
def delete_container(cid):
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
