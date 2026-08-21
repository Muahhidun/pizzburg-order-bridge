from app.api.routes.menu import MENU_CONTENT_TYPE
from app.core.config import Settings
from app.schemas.menu import MenuCategory, MenuComposition, MenuItem, MenuItemImage
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
                    images=[
                        MenuItemImage(
                            hash="a" * 40,
                            url="https://joinposter.com/pizza-125.jpg",
                        )
                    ],
                ),
                MenuItem(
                    id="118",
                    category_id="3",
                    name="Пепперони",
                    price=3150,
                    measure=577,
                    measure_unit="g",
                    images=[
                        MenuItemImage(
                            hash="b" * 40,
                            url="https://joinposter.com/pizza-118.jpg",
                        )
                    ],
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
    assert all(len(item["images"]) == 1 for item in body["items"])


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
                "photo_origin": "/upload/pizza-125.jpeg",
                "hidden": "0",
                "sort_order": "20",
                "out": 577,
                "unit": "kg",
                "spots": [{"spot_id": "1", "price": "255000", "visible": "1"}],
                "sources": [{"id": 3, "name": "Wolt", "price": "265000", "visible": 1}],
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

    async def get_image_hashes(self, urls):
        return {url: "c" * 40 for url in urls}


class FakeStorefrontClient:
    async def get_product_photos(self):
        return {}


async def test_poster_menu_service_maps_real_poster_fields():
    settings = Settings(poster_menu_category_id="3", poster_main_spot_id="1")
    service = PosterMenuService(
        settings,
        client=FakePosterClient(),
        storefront_client=FakeStorefrontClient(),
    )

    menu = await service.get_menu()

    assert menu.categories[0].id == "3"
    assert menu.categories[0].name == "Пицца"
    assert len(menu.items) == 1
    assert menu.items[0].id == "125"
    assert menu.items[0].name == "Маргарита"
    assert menu.items[0].price == 2650
    assert menu.items[0].measure == 525
    assert menu.items[0].measure_unit == "g"
    assert menu.items[0].description is not None
    assert menu.items[0].description.endswith("(30 см)")
    assert menu.items[0].images[0].hash == "c" * 40
    assert str(menu.items[0].images[0].url) == ("https://joinposter.com/upload/pizza-125.jpeg")


def test_meat_pizza_description_names_meat_types():
    from app.services.pizza_metadata import PIZZA_DESCRIPTIONS

    description = PIZZA_DESCRIPTIONS["169"]

    assert "куриная ветчина" in description
    assert "говяжьи гриль-сосиски" in description
    assert description.endswith("(30 см)")


def test_all_pizza_descriptions_have_composition_and_diameter():
    from app.services.pizza_metadata import PIZZA_DESCRIPTIONS

    assert len(PIZZA_DESCRIPTIONS) == 18
    assert all(value.startswith("Состав: ") for value in PIZZA_DESCRIPTIONS.values())
    assert all(value.endswith("(30 см)") for value in PIZZA_DESCRIPTIONS.values())
