from app.api.routes.menu import MENU_CONTENT_TYPE
from app.core.config import Settings
from app.schemas.menu import MenuCategory, MenuComposition, MenuItem
from app.services.poster_menu import PosterMenuService


async def test_menu_returns_poster_items_in_yandex_format(client, token, monkeypatch):
    async def fake_get_menu(_: PosterMenuService) -> MenuComposition:
        return MenuComposition(
            categories=[MenuCategory(id="3", name="Пиццы", sort_order=10)],
            items=[
                MenuItem(
                    id="125",
                    category_id="3",
                    name="Маргарита",
                    price=2550,
                    measure=577,
                    measure_unit="g",
                ),
                MenuItem(
                    id="118",
                    category_id="3",
                    name="Пепперони",
                    price=3150,
                    measure=577,
                    measure_unit="g",
                ),
            ],
            last_change="2026-08-10T11:00:00.000000+00:00",
        )

    monkeypatch.setattr(PosterMenuService, "get_menu", fake_get_menu)
    response = await client.get(
        "/menu/pizzburg-main/composition",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == MENU_CONTENT_TYPE
    body = response.json()
    assert body["lastChange"] == "2026-08-10T11:00:00.000000+00:00"
    assert body["categories"] == [{"id": "3", "name": "Пиццы", "sortOrder": 10}]
    assert len(body["items"]) == 2
    assert {item["id"] for item in body["items"]} == {"125", "118"}
    assert all(item["categoryId"] == "3" for item in body["items"])
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


class FakePosterClient:
    async def get_categories(self):
        return [
            {
                "category_id": "3",
                "category_name": "Пиццы",
                "category_hidden": "0",
                "sort_order": "11",
            }
        ]

    async def get_products(self):
        return [
            {
                "product_id": "125",
                "product_name": "Маргарита ",
                "menu_category_id": "3",
                "product_production_description": "",
                "hidden": "0",
                "sort_order": "20",
                "out": 577,
                "unit": "kg",
                "spots": [{"spot_id": "1", "price": "255000", "visible": "1"}],
            },
            {
                "product_id": "hidden",
                "product_name": "Скрытая пицца",
                "menu_category_id": "3",
                "hidden": "1",
                "out": 500,
                "unit": "kg",
                "price": {"1": "100000"},
            },
        ]


async def test_poster_menu_service_maps_real_poster_fields():
    settings = Settings(poster_menu_category_id="3", poster_main_spot_id="1")
    service = PosterMenuService(settings, client=FakePosterClient())

    menu = await service.get_menu()

    assert menu.categories[0].id == "3"
    assert menu.categories[0].name == "Пиццы"
    assert len(menu.items) == 1
    assert menu.items[0].id == "125"
    assert menu.items[0].name == "Маргарита"
    assert menu.items[0].price == 2550
    assert menu.items[0].measure == 577
    assert menu.items[0].measure_unit == "g"
