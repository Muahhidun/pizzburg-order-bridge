from app.adapters.storefront import normalize_product_name
from app.services.menu_metadata import EXCLUDED_PRODUCT_IDS, menu_description, menu_measure


def test_user_selected_products_are_excluded():
    assert EXCLUDED_PRODUCT_IDS == {"91", "171", "177"}


def test_user_selected_measure_overrides():
    assert menu_measure({"product_id": "115"}) == (300, "ml")
    assert menu_measure({"product_id": "57"}) == (25, "g")
    assert menu_measure({"product_id": "138"}) == (15, "g")


def test_food_measure_is_reduced_and_rounded_to_nearest_25_grams():
    assert menu_measure({"product_id": "189", "out": 277, "unit": "kg"}) == (250, "g")
    assert menu_measure({"product_id": "125", "out": 577, "unit": "kg"}) == (525, "g")


def test_description_uses_main_ingredients_and_filters_technical_components():
    product = {
        "product_id": "sample",
        "ingredients": [
            {"ingredient_name": "Филе курицы"},
            {"ingredient_name": "Лук простой"},
            {"ingredient_name": "Оливкое масло"},
            {"ingredient_name": "Упаковка бургер"},
        ],
    }

    assert menu_description(product) == "Состав: куриное филе, репчатый лук."


def test_storefront_name_normalization_handles_punctuation_and_yo():
    assert normalize_product_name("  Бургер «Тёплый» — XL ") == "бургер теплый xl"
