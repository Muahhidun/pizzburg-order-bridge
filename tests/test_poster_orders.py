from decimal import Decimal

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.schemas.order import YandexOrderCreate
from app.services.poster_orders import PosterOrderNotConfiguredError, PosterOrderService


class FakePosterClient:
    def __init__(self) -> None:
        self.payload = None

    async def create_incoming_order(self, payload):
        self.payload = payload
        return {"incoming_order_id": 321}


def _order(*, phone: str | None = "+77273470693") -> YandexOrderCreate:
    return YandexOrderCreate.model_validate(
        {
            "discriminator": "yandex",
            "eatsId": "260904-1234567",
            "restaurantId": "pizzburg-main",
            "deliveryInfo": {
                "clientName": "Яндекс.Еда",
                "phoneNumber": phone,
                "courierArrivementDate": "2026-09-04T18:30:00+05:00",
            },
            "paymentInfo": {"itemsCost": 1890, "paymentType": "CARD"},
            "items": [
                {
                    "id": "56",
                    "name": "Fuze Tea S",
                    "quantity": 1,
                    "price": 850,
                    "modifications": [
                        {
                            "id": "56-choice-1",
                            "group_id": "56-choice",
                            "name": "Лайм-мята",
                            "quantity": 1,
                            "price": 0,
                        }
                    ],
                    "promos": [],
                },
                {
                    "id": "142",
                    "name": "BBQ Бургер",
                    "quantity": Decimal("2"),
                    "price": 520,
                    "modifications": [],
                    "promos": [],
                },
            ],
            "persons": 2,
            "comment": "Не готовить — тест",
            "promos": [],
        }
    )


async def test_builds_and_creates_poster_incoming_order():
    client = FakePosterClient()
    settings = Settings(
        poster_main_token=SecretStr("poster-test-token"),
        poster_main_spot_id="1",
        poster_currency="KZT",
    )
    service = PosterOrderService(settings, client=client)

    poster_order_id = await service.create_order(_order())

    assert poster_order_id == "321"
    assert client.payload["spot_id"] == 1
    assert client.payload["service_mode"] == 3
    assert client.payload["delivery_time"] == "2026-09-04 18:30:00"
    assert client.payload["products"] == [
        {"product_id": 56, "count": 1, "price": 85000},
        {"product_id": 142, "count": 2, "price": 52000},
    ]
    assert client.payload["payment"] == {"type": 1, "sum": 189000, "currency": "KZT"}
    assert "Fuze Tea S: Лайм-мята × 1" in client.payload["comment"]
    assert "Не готовить — тест" in client.payload["comment"]


async def test_rejects_forwarding_without_phone():
    service = PosterOrderService(Settings(), client=FakePosterClient())

    with pytest.raises(PosterOrderNotConfiguredError):
        await service.create_order(_order(phone=None))
