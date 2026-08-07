async def test_health_reports_database(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_protected_route_requires_token(client):
    response = await client.get("/restaurants")

    assert response.status_code == 401
