from app.api.routes.menu import MENU_CONTENT_TYPE


async def test_menu_contains_two_yandex_test_items(client, token):
    response = await client.get(
        "/menu/pizzburg-main/composition",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == MENU_CONTENT_TYPE
    body = response.json()
    assert body["lastChange"] == "2026-08-10T16:00:00.000000+05:00"
    assert body["categories"] == [{"id": "test-pizzas", "name": "Тестовые пиццы", "sortOrder": 10}]
    assert len(body["items"]) == 2
    assert {item["id"] for item in body["items"]} == {
        "test-pizza-margherita",
        "test-pizza-pepperoni",
    }
    assert all(item["categoryId"] == "test-pizzas" for item in body["items"])
    assert all(item["price"] > 0 for item in body["items"])
    assert all(item["measureUnit"] == "g" for item in body["items"])


async def test_menu_requires_authorization(client):
    response = await client.get("/menu/pizzburg-main/composition")

    assert response.status_code == 401


async def test_unknown_restaurant_menu_returns_yandex_error_list(client, token):
    response = await client.get(
        "/menu/unknown/composition",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json() == [{"code": 404, "description": "Restaurant not found"}]
