from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.adapters.poster import PosterAPIError, PosterClient
from app.core.config import Settings
from app.schemas.order import YandexOrderCreate


class PosterOrderNotConfiguredError(Exception):
    pass


def _minor_units(value: Decimal) -> int:
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _count(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    return int(integral) if value == integral else float(value)


def _comment(order: YandexOrderCreate) -> str:
    lines = [f"Яндекс Еда №{order.eatsId}"]
    if order.paymentInfo.paymentType == "CARD":
        lines.append("Оплата: картой в Яндекс Еде")
    else:
        lines.append("Оплата: наличными")
    lines.append(f"Количество персон: {order.persons}")

    choices = [
        f"{item.name}: {modifier.name} × {_count(modifier.quantity)}"
        for item in order.items
        for modifier in item.modifications
    ]
    if choices:
        lines.append("Выбор: " + "; ".join(choices))
    if order.comment:
        lines.append(order.comment)
    return "\n".join(lines)


class PosterOrderService:
    def __init__(self, settings: Settings, client: PosterClient | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._settings.poster_order_forwarding_enabled

    def _poster_client(self) -> PosterClient:
        if self._client is not None:
            return self._client
        secret = self._settings.poster_main_token
        token = secret.get_secret_value() if secret is not None else ""
        if not token:
            raise PosterOrderNotConfiguredError
        return PosterClient(
            token=token,
            base_url=self._settings.poster_api_url,
            timeout_seconds=self._settings.poster_request_timeout_seconds,
        )

    def build_payload(self, order: YandexOrderCreate) -> dict[str, Any]:
        phone = (order.deliveryInfo.phoneNumber or "").strip()
        if not phone:
            raise PosterOrderNotConfiguredError("Yandex order has no customer phone")

        payload: dict[str, Any] = {
            "spot_id": int(self._settings.poster_main_spot_id),
            "first_name": order.deliveryInfo.clientName,
            "phone": phone,
            "skip_phone_validation": True,
            "service_mode": 3,
            "delivery_time": order.deliveryInfo.courierArrivementDate.strftime("%Y-%m-%d %H:%M:%S"),
            "comment": _comment(order),
            "products": [
                {
                    "product_id": int(item.id),
                    "count": _count(item.quantity),
                    "price": _minor_units(item.price),
                }
                for item in order.items
            ],
        }
        return payload

    async def create_order(self, order: YandexOrderCreate) -> str:
        result = await self._poster_client().create_incoming_order(self.build_payload(order))
        poster_order_id = str(result.get("incoming_order_id") or "").strip()
        if not poster_order_id:
            raise PosterAPIError("Poster returned no incoming_order_id")
        return poster_order_id
