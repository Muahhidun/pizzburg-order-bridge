import re
from math import floor
from typing import Any

from app.services.pizza_metadata import PIZZA_DESCRIPTIONS

EXCLUDED_PRODUCT_IDS = {"91", "171", "177"}

CATEGORY_NAME_OVERRIDES = {
    "3": "Пицца",
    "5": "Закуски",
    "7": "Дополнительно",
    "8": "Хот-доги",
    "20": "Детское меню",
}

ITEM_NAME_OVERRIDES = {
    "13": "BonAqua S",
    "59": "BonAqua M",
    "14": "Coca-Cola S",
    "15": "Coca-Cola M",
    "16": "Сок Piko S",
    "17": "Сок Piko M",
    "18": "Сок Piko тетрапак S",
    "19": "Сок Piko тетрапак M",
    "21": "Sprite S",
    "20": "Sprite M",
    "23": "Fanta S",
    "22": "Fanta M",
    "56": "Fuze Tea S",
    "55": "Fuze Tea M",
    "57": "Соус",
    "138": "Сыр",
    "139": "Грибы",
    "108": "Крылышки S",
    "109": "Крылышки M",
    "110": "Крылышки L",
    "181": "Донер большой говяжий",
    "180": "Донер в батоне говяжий",
    "182": "Донер маленький говяжий",
    "179": "Донер стандартный говяжий",
    "132": "Донер большой куриный",
    "134": "Донер в батоне куриный",
    "71": "Донер маленький куриный",
    "131": "Донер стандартный куриный",
    "47": "Чизбургер",
    "167": "Мини-бургер куриный",
    "166": "Мини-бургер говяжий",
    "141": "ЧикенЧиз Суперсырный",
    "129": "Хот-дог куриный",
    "128": "Хот-дог говяжий",
    "76": "Балоньезе",
    "176": "Курица барбекю",
    "124": "Четыре сыра",
    "123": "Четыре сезона",
    "114": "Курица ранч",
    "162": "Комбо Хот-дог",
}

MEASURE_OVERRIDES: dict[str, tuple[int, str]] = {
    "115": (300, "ml"),
    "13": (500, "ml"),
    "59": (1000, "ml"),
    "14": (500, "ml"),
    "15": (1000, "ml"),
    "16": (500, "ml"),
    "17": (1000, "ml"),
    "18": (200, "ml"),
    "19": (1000, "ml"),
    "21": (500, "ml"),
    "20": (1000, "ml"),
    "23": (500, "ml"),
    "22": (1000, "ml"),
    "56": (500, "ml"),
    "55": (1000, "ml"),
    "57": (25, "g"),
    "139": (40, "g"),
    "138": (15, "g"),
    "137": (20, "g"),
    "161": (850, "g"),
    "163": (950, "g"),
    "164": (1700, "g"),
    "162": (750, "g"),
    "150": (850, "g"),
    "174": (475, "g"),
    "173": (475, "g"),
}

DESCRIPTION_OVERRIDES = {
    "115": "Кисломолочный напиток айран.",
    "13": "Негазированная питьевая вода с нейтральным вкусом (500 мл).",
    "59": "Негазированная питьевая вода с нейтральным вкусом (1 л).",
    "14": "Освежающий газированный напиток (500 мл).",
    "15": "Освежающий газированный напиток (1 л).",
    "16": "Освежающий негазированный напиток со вкусом апельсина (500 мл).",
    "17": "Освежающий негазированный напиток со вкусом апельсина (1 л).",
    "18": "Освежающий негазированный сок со вкусом яблока (200 мл).",
    "19": ("Освежающий негазированный сок. Вкусы: яблоко, апельсин, компот (1 л)."),
    "21": "Освежающий газированный напиток (500 мл).",
    "20": "Освежающий газированный напиток (1 л).",
    "23": "Освежающий газированный напиток (500 мл).",
    "22": "Освежающий газированный напиток (1 л).",
    "56": (
        "Освежающий холодный чай. Вкусы: лайм-мята, лимон, ягоды, манго-ананас, персик (500 мл)."
    ),
    "55": ("Освежающий холодный чай. Вкусы: лайм-мята, лимон, ягоды, манго-ананас, персик (1 л)."),
    "57": "Добавка к блюдам.",
    "139": "Жареные шампиньоны.",
    "138": "Сыр чеддер.",
    "137": "Маринованный перец халапеньо (20 г).",
    "46": (
        "Состав: булочка с кунжутом, куриное филе, салат айсберг, помидоры, "
        "маринованные огурцы, соус тар-тар."
    ),
    "161": "Донер маленький куриный, фри, Coca-Cola (500 мл).",
    "163": "Крылышки (6 шт.), фри, Coca-Cola (500 мл).",
    "164": "Маргарита (30 см), фри, Coca-Cola (1 л).",
    "162": "Хот-дог куриный, фри, Coca-Cola (500 мл).",
    "150": "Чизбургер, Coca-Cola (500 мл).",
    "173": ("Фри, мини-бургер куриный, сок Piko тетрапак со вкусом яблока, игрушка-сюрприз."),
    "174": ("Фри, мини-бургер говяжий, сок Piko тетрапак со вкусом яблока, игрушка-сюрприз."),
    "108": "Состав: панировка, куриные крылышки, кетчуп (6 шт.).",
    "109": "Состав: панировка, куриные крылышки, кетчуп (12 шт.).",
    "110": "Состав: панировка, куриные крылышки, кетчуп (24 шт.).",
}

MODIFIER_GROUP_OVERRIDES: dict[str, list[dict[str, Any]]] = {
    "57": [
        {
            "id": "57-sauce-choice",
            "name": "Выберите соус",
            "minSelectedModifiers": 1,
            "maxSelectedModifiers": 1,
            "sortOrder": 0,
            "modifiers": [
                {
                    "id": "57-white",
                    "name": "Майонез",
                    "price": 0,
                    "minAmount": 0,
                    "maxAmount": 1,
                },
                {
                    "id": "57-red",
                    "name": "Кетчуп",
                    "price": 0,
                    "minAmount": 0,
                    "maxAmount": 1,
                },
                {
                    "id": "57-cheese",
                    "name": "Сырный соус",
                    "price": 0,
                    "minAmount": 0,
                    "maxAmount": 1,
                },
            ],
        }
    ]
}

_SKIP_INGREDIENTS = (
    "перчатк",
    "шпаж",
    "упаков",
    "уголок",
    "лодочк",
    "пакет ",
    "соус тары",
    "тесто пиццы",
    "оливкое масло",
    "орегано",
    "маринад крылья",
)

_INGREDIENT_REPLACEMENTS = (
    (r"моцарелла.*", "моцарелла"),
    (r"польпа.*", "томатный соус"),
    (r"ветчина из куриного филе.*", "куриная ветчина"),
    (r"ветчина \(смолл\)", "куриная ветчина"),
    (r"фарш", "говяжья котлета"),
    (r"маринад донер", "куриное донерное мясо"),
    (r"донер мясо \(говядина\)", "говяжье донерное мясо"),
    (r"сыр чеддер.*", "сыр чеддер"),
    (r"салат листья.*", "салат айсберг"),
    (r"помидоры", "помидоры"),
    (r"огурцы свежие.*", "свежие огурцы"),
    (r"маринованные огурцы.*", "маринованные огурцы"),
    (r"лук простой", "репчатый лук"),
    (r"булочка кунжут.*", "булочка с кунжутом"),
    (r"мини булочка.*", "мини-булочка"),
    (r"булочка бриош.*", "булочка бриошь"),
    (r"булочка черная.*", "чёрная булочка"),
    (r"булочка френчдог.*", "багет"),
    (r"булочка хот-дог.*", "булочка для хот-дога"),
    (r"соус барбекю.*", "соус барбекю"),
    (r"соус донер", "фирменный донерный соус"),
    (r"соус сырный.*", "сырный соус"),
    (r"кетчуп.*", "кетчуп"),
    (r"халапеньо.*", "халапеньо"),
    (r"пепперони.*", "пепперони"),
    (r"сосиски говяжие.*", "говяжья сосиска"),
    (r"сосиски куриные.*", "куриная сосиска"),
    (r"филе курицы", "куриное филе"),
    (r"крыло курицы", "куриные крылышки"),
    (r"крылышки \d+шт упаковка.*", ""),
    (r"фри упаковка", ""),
    (r"фри", "картофель фри"),
    (r"наггетсы", "куриные наггетсы"),
    (r"панировочная смесь", "панировка"),
    (r"багет для донера", "багет"),
    (r"лаваш сырный", "сырный лаваш"),
    (r"тортилья сырная.*", "сырная тортилья"),
)


def menu_measure(product: dict[str, Any]) -> tuple[int, str] | None:
    product_id = str(product.get("product_id", ""))
    if product_id in MEASURE_OVERRIDES:
        return MEASURE_OVERRIDES[product_id]

    value = round(float(product.get("out") or 0))
    unit = str(product.get("unit") or "").lower()
    if value <= 0:
        return None
    if unit in {"kg", "g", "г"}:
        reduced = floor((value * 0.9) / 25 + 0.5) * 25
        if reduced >= value:
            reduced = floor((value - 1) / 25) * 25
        return max(25, reduced), "g"
    if unit in {"l", "liter", "litre", "ml", "мл"}:
        return value, "ml"
    return None


def _clean_ingredient(value: str) -> str | None:
    normalized = " ".join(value.strip().lower().split())
    if not normalized or any(part in normalized for part in _SKIP_INGREDIENTS):
        return None
    for pattern, replacement in _INGREDIENT_REPLACEMENTS:
        if re.fullmatch(pattern, normalized):
            return replacement or None
    normalized = re.sub(r"\s*\([^)]*(?:шт|гр|кг|л|мл)[^)]*\)", "", normalized)
    normalized = re.sub(r"\s+\d+(?:[,.]\d+)?\s*(?:кг|гр|г|л|мл).*", "", normalized)
    return normalized.strip() or None


def _combo_description(product: dict[str, Any]) -> str | None:
    components: list[str] = []
    for group in product.get("group_modifications") or []:
        for modification in group.get("modifications") or []:
            value = str(modification.get("name") or "")
            value = re.sub(r"\s*\([^)]*комбо[^)]*\)", "", value, flags=re.I)
            value = value.strip()
            if value:
                components.append(value)
    if not components:
        return None
    if str(product.get("menu_category_id")) == "20":
        components.append("игрушка-сюрприз")
    return f"Состав набора: {', '.join(components)}."


def menu_description(product: dict[str, Any]) -> str | None:
    product_id = str(product.get("product_id", ""))
    if product_id in PIZZA_DESCRIPTIONS:
        return PIZZA_DESCRIPTIONS[product_id]
    if product_id in DESCRIPTION_OVERRIDES:
        return DESCRIPTION_OVERRIDES[product_id]

    combo = _combo_description(product)
    if combo is not None:
        return combo

    ingredients: list[str] = []
    for ingredient in product.get("ingredients") or []:
        cleaned = _clean_ingredient(str(ingredient.get("ingredient_name") or ""))
        if cleaned and cleaned not in ingredients:
            ingredients.append(cleaned)
    if not ingredients:
        return None
    return f"Состав: {', '.join(ingredients)}."
