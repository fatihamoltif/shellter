def test_worker_register_without_token_is_rejected(client, app):
    app.config["AGENT_TOKEN"] = "token-test-s9"

    response = client.post(
        "/workers/register",
        json={
            "hostname": "worker-security-test",
            "ip": "192.168.56.99",
            "cpu": 1,
            "memory": 512,
        },
    )

    assert response.status_code == 401


def test_worker_register_with_wrong_token_is_rejected(client, app):
    app.config["AGENT_TOKEN"] = "token-test-s9"

    response = client.post(
        "/workers/register",
        headers={
            "Authorization": "Bearer mauvais-token"
        },
        json={
            "hostname": "worker-security-test",
            "ip": "192.168.56.99",
            "cpu": 1,
            "memory": 512,
        },
    )

    assert response.status_code == 401


def test_worker_register_with_valid_token_is_accepted(client, app):
    app.config["AGENT_TOKEN"] = "token-test-s9"

    response = client.post(
        "/workers/register",
        headers={
            "Authorization": "Bearer token-test-s9"
        },
        json={
            "hostname": "worker-security-valid",
            "ip": "192.168.56.99",
            "cpu": 1,
            "memory": 512,
        },
    )

    assert response.status_code == 200