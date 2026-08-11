async def test_health_reports_database(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_protected_route_requires_token(client):
    response = await client.get("/restaurants")

    assert response.status_code == 401


async def test_restaurants_uses_yandex_places_contract(client, token):
    response = await client.get(
        "/restaurants",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "places": [
            {
                "id": "pizzburg-main",
                "title": "PizzBurg",
                "address": ("Казахстан, Экибастуз, ул. Ауэзова, 47Б, ТРЦ MaxiMall"),
            }
        ]
    }
