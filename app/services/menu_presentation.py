"""Presentation for the existing pizzburg-main export; never writes to Poster."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.menu import MenuCategory, MenuItem

# Unknown categories follow the known menu instead of disappearing.
CATEGORY_ORDER = ("18", "3", "2", "6", "8", "4", "5", "7", "1", "20")
PRODUCT_FAMILIES = (
    ("71", "131", "132"),  # Chicken doner: small, regular, large.
    ("182", "179", "181"),  # Beef doner: small, regular, large.
    ("134", "180"),  # Baguettes must not split either doner trio.
    ("108", "109", "110"),
    ("13", "59"),
    ("14", "15"),
    ("16", "17"),
    ("21", "20"),
    ("23", "22"),
    ("56", "55"),
)
DRINK_BRAND_ORDER = ("13", "56", "14", "21", "23", "16", "19")


@lru_cache
def photo_overrides() -> dict[str, str]:
    path = Path(__file__).with_name("menu_photo_overrides.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _group_key(product_id: str) -> str:
    return next((family[0] for family in PRODUCT_FAMILIES if product_id in family), product_id)


def _ordered_items(items: list[MenuItem]) -> list[MenuItem]:
    groups: dict[str, list[MenuItem]] = {}
    for item in items:
        groups.setdefault(_group_key(item.id), []).append(item)

    def group_rank(entry: tuple[str, list[MenuItem]]) -> tuple[Any, ...]:
        key, members = entry
        # Owner's explicit first row: ayran, then 200 ml Piko, before paired bottles.
        prefix = {"115": 0, "18": 1}.get(key, 2) if members[0].category_id == "1" else 2
        brand = DRINK_BRAND_ORDER.index(key) if key in DRINK_BRAND_ORDER else 100
        return prefix, min(item.price for item in members), brand, members[0].name.casefold(), key

    result = []
    for key, members in sorted(groups.items(), key=group_rank):
        family = next((family for family in PRODUCT_FAMILIES if family[0] == key), ())
        ordered = sorted(
            members,
            key=lambda item: (
                family.index(item.id) if item.id in family else 100,
                item.price,
                item.name.casefold(),
                item.id,
            ),
        )
        result.extend(ordered)
    return result


def apply_menu_order(
    categories: list[MenuCategory], items: list[MenuItem]
) -> tuple[list[MenuCategory], list[MenuItem]]:
    category_indices = {category_id: index for index, category_id in enumerate(CATEGORY_ORDER)}
    ordered_categories = sorted(
        categories,
        key=lambda category: (
            category_indices.get(category.id, len(CATEGORY_ORDER)),
            category.sort_order,
            category.name.casefold(),
            category.id,
        ),
    )
    ordered_items = []
    for index, category in enumerate(ordered_categories, start=1):
        ordered_categories[index - 1] = category.model_copy(update={"sort_order": index * 10})
        members = _ordered_items([item for item in items if item.category_id == category.id])
        ordered_items.extend(
            item.model_copy(update={"sort_order": rank * 10})
            for rank, item in enumerate(members, start=1)
        )
    return ordered_categories, ordered_items
