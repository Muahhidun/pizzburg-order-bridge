import asyncio
import hashlib
import json
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from app.adapters.poster import PosterAPIError, PosterClient
from app.adapters.storefront import StorefrontClient, storefront_photo_keys
from app.core.config import Settings
from app.schemas.menu import MenuCategory, MenuComposition, MenuItem, MenuItemImage
from app.services.menu_metadata import (
    CATEGORY_NAME_OVERRIDES,
    EXCLUDED_PRODUCT_IDS,
    ITEM_NAME_OVERRIDES,
    MODIFIER_GROUP_OVERRIDES,
    menu_description,
    menu_measure,
)


class PosterNotConfiguredError(Exception):
    pass


def _number(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _source(product: dict[str, Any], source_name: str) -> dict[str, Any] | None:
    return next(
        (
            source
            for source in product.get("sources") or []
            if str(source.get("name") or "").casefold() == source_name.casefold()
        ),
        None,
    )


def _item_price(product: dict[str, Any], spot_id: str, source_name: str) -> float:
    source = _source(product, source_name)
    if source is not None:
        return _number(source.get("price")) / 100

    spots = product.get("spots")
    if isinstance(spots, list):
        spot = next(
            (item for item in spots if str(item.get("spot_id")) == spot_id),
            spots[0] if spots else None,
        )
        if isinstance(spot, dict):
            return _number(spot.get("price")) / 100

    prices = product.get("price")
    if isinstance(prices, dict):
        raw_price = prices.get(spot_id)
        if raw_price is None and prices:
            raw_price = next(iter(prices.values()))
        return _number(raw_price) / 100
    return 0


def _is_visible(product: dict[str, Any], spot_id: str, source_name: str) -> bool:
    if str(product.get("hidden", "0")) == "1":
        return False
    source = _source(product, source_name)
    if source is None or str(source.get("visible", "1")) == "0":
        return False
    spots = product.get("spots")
    if not isinstance(spots, list):
        return True
    spot = next(
        (item for item in spots if str(item.get("spot_id")) == spot_id),
        spots[0] if spots else None,
    )
    return not isinstance(spot, dict) or str(spot.get("visible", "1")) != "0"


def _measure_unit(poster_unit: Any) -> str | None:
    normalized = str(poster_unit or "").lower()
    if normalized in {"kg", "g", "г"}:
        return "g"
    if normalized in {"l", "liter", "litre", "ml", "мл"}:
        return "ml"
    return None


def _photo_url(poster_photo: Any) -> str | None:
    value = str(poster_photo or "").strip()
    if not value:
        return None
    if value.startswith("https://"):
        return value
    if value.startswith("/"):
        return f"https://joinposter.com{value}"
    return None


class PosterMenuService:
    def __init__(
        self,
        settings: Settings,
        client: PosterClient | None = None,
        storefront_client: StorefrontClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._storefront_client = storefront_client or StorefrontClient(
            settings.storefront_menu_url,
            timeout_seconds=settings.poster_request_timeout_seconds,
        )
        self._cached_menu: MenuComposition | None = None
        self._cached_until = 0.0
        self._signature: str | None = None
        self._last_change: str | None = None
        self._lock = asyncio.Lock()

    def _poster_client(self) -> PosterClient:
        if self._client is not None:
            return self._client
        secret = self._settings.poster_main_token
        token = secret.get_secret_value() if secret is not None else ""
        if not token:
            raise PosterNotConfiguredError
        return PosterClient(
            token=token,
            base_url=self._settings.poster_api_url,
            timeout_seconds=self._settings.poster_request_timeout_seconds,
        )

    async def get_menu(self) -> MenuComposition:
        if self._cached_menu is not None and monotonic() < self._cached_until:
            return self._cached_menu

        async with self._lock:
            if self._cached_menu is not None and monotonic() < self._cached_until:
                return self._cached_menu
            menu = await self._load_menu()
            self._cached_menu = menu
            self._cached_until = monotonic() + self._settings.poster_menu_cache_seconds
            return menu

    async def _load_menu(self) -> MenuComposition:
        client = self._poster_client()
        categories, products, storefront_photos = await asyncio.gather(
            client.get_categories(),
            client.get_products(),
            self._storefront_client.get_product_photos(),
        )

        active_categories = sorted(
            (item for item in categories if str(item.get("category_hidden", "0")) != "1"),
            key=lambda item: _integer(item.get("sort_order"), 100),
        )

        prepared_items: list[dict[str, Any]] = []
        menu_categories: list[MenuCategory] = []
        for category in active_categories:
            category_id = str(category.get("category_id", "")).strip()
            category_products = sorted(
                (
                    product
                    for product in products
                    if str(product.get("menu_category_id")) == category_id
                ),
                key=lambda product: _integer(product.get("sort_order"), 100),
            )
            category_item_count = 0
            for product in category_products:
                if not _is_visible(
                    product,
                    self._settings.poster_main_spot_id,
                    self._settings.poster_menu_price_source,
                ):
                    continue

                product_id = str(product.get("product_id", "")).strip()
                if product_id in EXCLUDED_PRODUCT_IDS:
                    continue
                poster_name = str(product.get("product_name", "")).strip()
                name = ITEM_NAME_OVERRIDES.get(product_id, poster_name)
                price = _item_price(
                    product,
                    self._settings.poster_main_spot_id,
                    self._settings.poster_menu_price_source,
                )
                measure = menu_measure(product)
                description = menu_description(product)
                photo_url = next(
                    (
                        storefront_photos[key]
                        for key in storefront_photo_keys(product_id, poster_name)
                        if key in storefront_photos
                    ),
                    None,
                )
                if photo_url is None:
                    photo_url = _photo_url(product.get("photo_origin") or product.get("photo"))
                if (
                    not product_id
                    or not name
                    or price <= 0
                    or measure is None
                    or description is None
                    or photo_url is None
                ):
                    continue

                prepared_items.append(
                    {
                        "id": product_id,
                        "category_id": category_id,
                        "name": name,
                        "description": description,
                        "price": price,
                        "measure": measure[0],
                        "measure_unit": measure[1],
                        "sort_order": _integer(product.get("sort_order"), 100),
                        "modifier_groups": MODIFIER_GROUP_OVERRIDES.get(product_id, []),
                        "photo_url": photo_url,
                    }
                )
                category_item_count += 1

            if category_item_count:
                menu_categories.append(
                    MenuCategory(
                        id=category_id,
                        name=CATEGORY_NAME_OVERRIDES.get(
                            category_id,
                            str(category.get("category_name") or "").strip(),
                        ),
                        sort_order=_integer(category.get("sort_order"), 100),
                    )
                )

        if not prepared_items:
            raise PosterAPIError("Poster menu contains no valid items")

        image_hashes = await client.get_image_hashes([item["photo_url"] for item in prepared_items])
        menu_items = [
            MenuItem(
                id=item["id"],
                category_id=item["category_id"],
                name=item["name"],
                description=item["description"],
                price=item["price"],
                measure=item["measure"],
                measure_unit=item["measure_unit"],
                sort_order=item["sort_order"],
                modifier_groups=item["modifier_groups"],
                images=[
                    MenuItemImage(
                        hash=image_hashes[item["photo_url"]],
                        url=item["photo_url"],
                    )
                ],
            )
            for item in prepared_items
        ]
        content = {
            "categories": [
                category.model_dump(mode="json", by_alias=True) for category in menu_categories
            ],
            "items": [item.model_dump(mode="json", by_alias=True) for item in menu_items],
        }
        signature = hashlib.sha256(
            json.dumps(content, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        if signature != self._signature or self._last_change is None:
            self._signature = signature
            self._last_change = datetime.now(UTC).isoformat(timespec="microseconds")

        return MenuComposition(
            categories=menu_categories,
            items=menu_items,
            last_change=self._last_change,
        )
