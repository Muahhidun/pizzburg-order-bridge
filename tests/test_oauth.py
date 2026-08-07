import base64


async def test_client_credentials_form_returns_token(client):
    response = await client.post(
        "/security/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "test-client",
            "client_secret": "test-secret",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 900


async def test_client_credentials_basic_auth_returns_token(client):
    encoded = base64.b64encode(b"test-client:test-secret").decode()
    response = await client.post(
        "/security/oauth/token",
        headers={"Authorization": f"Basic {encoded}"},
        data={"grant_type": "client_credentials"},
    )

    assert response.status_code == 200


async def test_invalid_client_is_rejected(client):
    response = await client.post(
        "/security/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "test-client",
            "client_secret": "wrong-secret",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_client"
