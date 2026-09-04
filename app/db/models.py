from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("provider", "external_order_id", name="uq_order_provider_external_id"),
        Index("ix_orders_restaurant_id", "restaurant_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_order_id: Mapped[str] = mapped_column(String(128), nullable=False)
    restaurant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    forwarding_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_requested", server_default="not_requested"
    )
    poster_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    forwarding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
