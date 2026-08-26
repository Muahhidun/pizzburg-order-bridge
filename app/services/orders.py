import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order
from app.schemas.order import OrderCreate


class DuplicateOrderConflictError(Exception):
    pass


def _payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def find_order(session: AsyncSession, external_order_id: str) -> Order | None:
    result = await session.execute(
        select(Order).where(Order.external_order_id == external_order_id)
    )
    return result.scalar_one_or_none()


async def save_dry_run_order(
    session: AsyncSession,
    request: OrderCreate,
    *,
    source_payload: dict | None = None,
) -> tuple[Order, bool]:
    payload = source_payload or request.model_dump(mode="json")
    digest = _payload_hash(payload)
    now = datetime.now(UTC)
    order = Order(
        id=str(uuid4()),
        provider=request.provider,
        external_order_id=request.external_order_id,
        restaurant_id=request.restaurant_id,
        status="accepted_dry_run",
        mode="dry-run",
        payload=payload,
        payload_hash=digest,
        created_at=now,
        updated_at=now,
    )
    session.add(order)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(Order).where(
                Order.provider == request.provider,
                Order.external_order_id == request.external_order_id,
            )
        )
        existing = result.scalar_one()
        if existing.payload_hash != digest:
            raise DuplicateOrderConflictError from None
        return existing, True

    await session.refresh(order)
    return order, False
