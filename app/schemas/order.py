from datetime import datetime
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
    quantity: int = Field(ge=1, le=100)
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
