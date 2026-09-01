from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)


class DeliveryAddress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_address: str = Field(min_length=1, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_item_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(gt=0, le=100)
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    modifiers: list[str] = Field(default_factory=list)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["yandex", "wolt"] = "yandex"
    external_order_id: str = Field(min_length=1, max_length=128)
    restaurant_id: Literal["pizzburg-main"]
    currency: Literal["KZT"] = "KZT"
    customer: Customer
    delivery_address: DeliveryAddress | None = None
    items: list[OrderItem] = Field(min_length=1, max_length=200)
    total: Decimal = Field(ge=0, decimal_places=2)
    comment: str | None = Field(default=None, max_length=1000)
    created_at: datetime

    @model_validator(mode="after")
    def total_must_match_items(self) -> "OrderCreate":
        calculated = sum((item.unit_price * item.quantity for item in self.items), Decimal("0"))
        if calculated != self.total:
            raise ValueError("total must equal the sum of item prices")
        return self


class OrderResponse(BaseModel):
    id: str
    provider: str
    external_order_id: str
    restaurant_id: str
    status: str
    mode: str
    duplicate: bool = False
    created_at: datetime
    updated_at: datetime


class OrderStatusResponse(BaseModel):
    external_order_id: str
    status: str
    mode: str
    updated_at: datetime


class YandexOrderModification(BaseModel):
    """Modifier from the Yandex Eats order v2 contract."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1, max_length=128)
    group_id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(ge=0, decimal_places=2)


class YandexOrderItem(BaseModel):
    """Menu item from the Yandex Eats order v2 contract."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(ge=0, decimal_places=2)
    modifications: list[YandexOrderModification] = Field(default_factory=list)
    promos: list[dict | None] = Field(default_factory=list)
    comboInfo: dict | None = None


class YandexDeliveryInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    clientName: str = Field(min_length=1, max_length=200)
    phoneNumber: str | None = Field(default=None, max_length=64)
    courierArrivementDate: datetime
    additionalPhoneNumbers: list[str | None] = Field(default_factory=list)
    realPhoneNumber: str | None = Field(default=None, max_length=64)
    pickupCode: str | None = Field(default=None, max_length=64)
    batches: list[str] = Field(default_factory=list)


class YandexPaymentInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    itemsCost: Decimal = Field(ge=0, decimal_places=2)
    paymentType: Literal["CARD", "CASH"]


class YandexOrderCreate(BaseModel):
    """Official ``application/vnd.eats.order.v2+json`` delivery payload."""

    model_config = ConfigDict(extra="allow")

    platform: str | None = Field(default=None, max_length=32)
    discriminator: Literal["yandex"]
    eatsId: str = Field(min_length=1, max_length=128)
    restaurantId: Literal["pizzburg-main"]
    deliveryInfo: YandexDeliveryInfo
    paymentInfo: YandexPaymentInfo
    items: list[YandexOrderItem] = Field(min_length=1, max_length=200)
    persons: int = Field(ge=0)
    comment: str | None = Field(default=None, max_length=2000)
    promos: list[dict | None] = Field(default_factory=list)

    def to_internal_order(self) -> OrderCreate:
        items = [
            OrderItem(
                external_item_id=item.id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.price,
                modifiers=[modifier.name for modifier in item.modifications],
            )
            for item in self.items
        ]
        calculated_total = sum((item.unit_price * item.quantity for item in items), Decimal("0"))
        return OrderCreate(
            provider="yandex",
            external_order_id=self.eatsId,
            restaurant_id=self.restaurantId,
            customer=Customer(
                name=self.deliveryInfo.clientName,
                phone=self.deliveryInfo.phoneNumber,
            ),
            items=items,
            total=calculated_total,
            comment=self.comment,
            created_at=datetime.now(UTC),
        )


class YandexOrderCreateResponse(BaseModel):
    result: Literal["OK"] = "OK"
    orderId: str


class YandexOrderStatusResponse(BaseModel):
    status: Literal[
        "NEW",
        "ACCEPTED_BY_RESTAURANT",
        "COOKING",
        "READY",
        "TAKEN_BY_COURIER",
        "DELIVERED",
        "CANCELLED",
    ]
    comment: str | None = Field(default=None, max_length=500)
    updatedAt: datetime | None = None
