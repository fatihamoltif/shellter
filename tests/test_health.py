def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_health_db_down(client, monkeypatch):
    from app.extensions import db

    def broken_execute(*args, **kwargs):
        raise Exception("DB down")

    monkeypatch.setattr(db.session, "execute", broken_execute)

    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "unavailable"
