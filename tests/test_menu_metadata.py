from app.adapters.storefront import normalize_product_name
from app.services.menu_metadata import (
    CATEGORY_NAME_OVERRIDES,
    DESCRIPTION_OVERRIDES,
    EXCLUDED_PRODUCT_IDS,
    ITEM_NAME_OVERRIDES,
    MODIFIER_GROUP_OVERRIDES,
    menu_description,
    menu_measure,
)
from app.services.pizza_metadata import PIZZA_DESCRIPTIONS


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


def test_manager_category_and_item_name_corrections():
    assert CATEGORY_NAME_OVERRIDES == {
        "3": "Пицца",
        "5": "Закуски",
        "7": "Дополнительно",
        "8": "Хот-доги",
        "20": "Детское меню",
    }
    assert ITEM_NAME_OVERRIDES["108"] == "Крылышки S"
    assert ITEM_NAME_OVERRIDES["109"] == "Крылышки M"
    assert ITEM_NAME_OVERRIDES["110"] == "Крылышки L"
    assert ITEM_NAME_OVERRIDES["71"] == "Донер маленький куриный"


def test_fuze_descriptions_include_all_current_flavors_and_volume():
    for product_id, volume in (("56", "500 мл"), ("55", "1 л")):
        description = DESCRIPTION_OVERRIDES[product_id]
        assert volume in description
        for flavor in ("лайм-мята", "лимон", "ягоды", "манго-ананас", "персик"):
            assert flavor in description


def test_drink_tastes_are_required_modifier_choices():
    assert MODIFIER_GROUP_OVERRIDES["55"][0]["name"] == "На выбор"
    assert MODIFIER_GROUP_OVERRIDES["56"][0]["name"] == "На выбор"
    assert MODIFIER_GROUP_OVERRIDES["19"][0]["name"] == "На выбор"
    assert [modifier["name"] for modifier in MODIFIER_GROUP_OVERRIDES["55"][0]["modifiers"]] == [
        "Лайм-мята",
        "Лимон",
        "Ягоды",
        "Манго-ананас",
        "Персик",
    ]
    assert [modifier["name"] for modifier in MODIFIER_GROUP_OVERRIDES["19"][0]["modifiers"]] == [
        "Яблоко",
        "Апельсин",
        "Компот",
    ]


def test_ketchunez_spelling_is_normalized_in_ingredients():
    product = {
        "product_id": "sample",
        "ingredients": [{"ingredient_name": "Соус кичинез"}],
    }
    assert menu_description(product) == "Состав: соус кетчунез."


def test_combo_doner_uses_small_chicken_doner():
    assert DESCRIPTION_OVERRIDES["161"].startswith("Донер маленький куриный")


def test_kids_menu_uses_the_usual_apple_piko_tetrapak():
    assert "вкусом яблока" in DESCRIPTION_OVERRIDES["18"]
    assert "вкусом яблока" in DESCRIPTION_OVERRIDES["173"]
    assert "вкусом яблока" in DESCRIPTION_OVERRIDES["174"]


def test_sauce_requires_one_choice_from_three_options():
    group = MODIFIER_GROUP_OVERRIDES["57"][0]
    assert group["minSelectedModifiers"] == 1
    assert group["maxSelectedModifiers"] == 1
    assert [modifier["name"] for modifier in group["modifiers"]] == [
        "Майонез",
        "Кетчуп",
        "Сырный соус",
    ]


def test_pizza_diameter_follows_manager_format_without_period():
    assert all(value.endswith("(30 см)") for value in PIZZA_DESCRIPTIONS.values())
    assert all(". (30 см)" not in value for value in PIZZA_DESCRIPTIONS.values())
