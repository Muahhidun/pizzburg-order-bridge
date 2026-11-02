from urllib.parse import urlparse

import pytest

from app.schemas.menu import MenuCategory, MenuItem, MenuItemImage
from app.services.menu_presentation import apply_menu_order, photo_overrides


def item(product_id, category, price):
    return MenuItem(
        id=product_id,
        category_id=category,
        name=f"Product {product_id}",
        description="Existing recipe",
        price=price,
        measure=500,
        measure_unit="g",
        images=[MenuItemImage(hash="a" * 40, url="https://example.com/photo.jpg")],
    )


def test_category_order_keeps_unknown_categories_and_business_fields():
    categories = [MenuCategory(id=i, name=i) for i in ["1", "20", "2", "18", "3", "new"]]
    items = [item(str(n), c.id, 100 + n) for n, c in enumerate(categories)]
    before = {i.id: i.model_dump(exclude={"sort_order"}) for i in items}

    ordered_categories, ordered_items = apply_menu_order(categories, items)

    assert [c.id for c in ordered_categories] == ["18", "3", "2", "1", "20", "new"]
    assert [c.sort_order for c in ordered_categories] == [10, 20, 30, 40, 50, 60]
    assert {i.id: i.model_dump(exclude={"sort_order"}) for i in ordered_items} == before
    assert all(c.sort_order == 100 for c in categories)  # Inputs are not mutated.


def test_burgers_follow_price_even_when_source_is_alphabetical():
    burgers = [item("bbq", "2", 1890), item("double", "2", 2590), item("mini", "2", 950)]
    _, result = apply_menu_order([MenuCategory(id="2", name="Бургеры")], burgers)
    assert [i.id for i in result] == ["mini", "bbq", "double"]
    assert [i.sort_order for i in result] == [10, 20, 30]


def test_doner_trios_are_not_split_by_cheaper_grill_or_baguette():
    prices = {
        "135": 1190,
        "71": 1290,
        "131": 1690,
        "132": 1990,
        "182": 1690,
        "179": 1990,
        "181": 2190,
        "178": 1790,
        "134": 1890,
        "180": 2090,
    }
    _, result = apply_menu_order(
        [MenuCategory(id="6", name="Донер")],
        [item(k, "6", v) for k, v in reversed(prices.items())],
    )
    assert [i.id for i in result] == list(prices)


@pytest.mark.parametrize("missing", [None, "13", "131"])
def test_pairs_and_partial_families_do_not_create_or_lose_items(missing):
    prices = {
        "115": 450,
        "18": 450,
        "13": 450,
        "59": 550,
        "56": 600,
        "55": 800,
        "14": 650,
        "15": 850,
        "21": 650,
        "20": 850,
        "23": 650,
        "22": 850,
        "16": 750,
        "17": 1050,
        "19": 1050,
    }
    source = [item(k, "1", v) for k, v in reversed(prices.items()) if k != missing]
    _, result = apply_menu_order([MenuCategory(id="1", name="Напитки")], source)
    assert len(result) == len(source)
    assert {i.id for i in result} == {i.id for i in source}
    assert [i.id for i in result][:2] == ["115", "18"]
    ids = [i.id for i in result]
    for small, large in [
        ("13", "59"),
        ("14", "15"),
        ("16", "17"),
        ("21", "20"),
        ("23", "22"),
        ("56", "55"),
    ]:
        if small in ids and large in ids:
            assert ids.index(large) == ids.index(small) + 1


def test_approved_photos_are_public_assets_and_unknown_items_have_fallback():
    photos = photo_overrides()
    assert all(
        urlparse(url).scheme == "https"
        and urlparse(url).hostname
        in {"pub-7710648eb70b40f0bcf08a208128f925.r2.dev", "joinposter.com"}
        and not urlparse(url).query
        for url in photos.values()
    )
    assert "unknown-future-product" not in photos
