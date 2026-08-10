import asyncio
import hashlib
import json
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from app.adapters.poster import PosterAPIError, PosterClient
from app.core.config import Settings
from app.schemas.menu import MenuCategory, MenuComposition, MenuItem


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


def _item_price(product: dict[str, Any], spot_id: str) -> float:
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


def _is_visible(product: dict[str, Any], spot_id: str) -> bool:
    if str(product.get("hidden", "0")) == "1":
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


class PosterMenuService:
    def __init__(self, settings: Settings, client: PosterClient | None = None) -> None:
        self._settings = settings
        self._client = client
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
        categories, products = await asyncio.gather(
            client.get_categories(),
            client.get_products(),
        )

        category_id = self._settings.poster_menu_category_id
        category = next(
            (
                item
                for item in categories
                if str(item.get("category_id")) == category_id
                and str(item.get("category_hidden", "0")) != "1"
            ),
            None,
        )
        if category is None:
            raise PosterAPIError("Poster pizza category is unavailable")

        menu_items: list[MenuItem] = []
        for product in products:
            if str(product.get("menu_category_id")) != category_id:
                continue
            if not _is_visible(product, self._settings.poster_main_spot_id):
                continue

            product_id = str(product.get("product_id", "")).strip()
            name = str(product.get("product_name", "")).strip()
            price = _item_price(product, self._settings.poster_main_spot_id)
            measure = round(_number(product.get("out")))
            measure_unit = _measure_unit(product.get("unit"))
            if not product_id or not name or price <= 0 or measure <= 0 or measure_unit is None:
                continue

            description = str(product.get("product_production_description") or "").strip()
            menu_items.append(
                MenuItem(
                    id=product_id,
                    category_id=category_id,
                    name=name,
                    description=description or None,
                    price=price,
                    measure=measure,
                    measure_unit=measure_unit,
                    sort_order=_integer(product.get("sort_order"), 100),
                )
            )

        if not menu_items:
            raise PosterAPIError("Poster pizza category contains no valid items")
        menu_items.sort(key=lambda item: (item.sort_order, item.name))

        category_name = str(category.get("category_name") or "Пиццы").strip()
        category_sort_order = _integer(category.get("sort_order"), 100)
        content = {
            "categories": [
                {
                    "id": category_id,
                    "name": category_name,
                    "sortOrder": category_sort_order,
                }
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
            categories=[
                MenuCategory(
                    id=category_id,
                    name=category_name,
                    sort_order=category_sort_order,
                )
            ],
            items=menu_items,
            last_change=self._last_change,
        )
