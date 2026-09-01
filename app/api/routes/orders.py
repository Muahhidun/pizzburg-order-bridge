from datetime import UTC
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session, require_access_token
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusResponse,
    YandexOrderCreate,
    YandexOrderCreateResponse,
    YandexOrderStatusResponse,
)
from app.services.orders import DuplicateOrderConflictError, find_order, save_dry_run_order

router = APIRouter(tags=["orders"], dependencies=[Depends(require_access_token)])


def _yandex_json(model: YandexOrderCreate) -> dict:
    return jsonable_encoder(
        model.model_dump(mode="python", by_alias=True, exclude_none=True),
        custom_encoder={Decimal: float},
    )


def _response(order, duplicate: bool = False) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        provider=order.provider,
        external_order_id=order.external_order_id,
        restaurant_id=order.restaurant_id,
        status=order.status,
        mode=order.mode,
        duplicate=duplicate,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post(
    "/order",
    response_model=OrderResponse | YandexOrderCreateResponse,
    status_code=status.HTTP_200_OK,
)
async def create_order(
    request: YandexOrderCreate | OrderCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse | YandexOrderCreateResponse:
    is_yandex_contract = isinstance(request, YandexOrderCreate)
    if is_yandex_contract:
        source_payload = _yandex_json(request)
        internal_request = request.to_internal_order()
    else:
        source_payload = None
        internal_request = request

    try:
        order, duplicate = await save_dry_run_order(
            session,
            internal_request,
            source_payload=source_payload,
        )
    except DuplicateOrderConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order ID already exists with different content",
        ) from exc
    if is_yandex_contract:
        response.status_code = status.HTTP_200_OK
        return YandexOrderCreateResponse(orderId=order.id)
    if duplicate:
        response.status_code = status.HTTP_200_OK
    return _response(order, duplicate)


def _is_yandex_order_payload(payload: dict) -> bool:
    return payload.get("discriminator") == "yandex" and "eatsId" in payload


def _not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=[{"code": 404, "description": "Order not found"}],
    )


@router.get("/order/{order_id}", response_model=OrderResponse | YandexOrderCreate)
async def get_order(
    order_id: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> OrderResponse | YandexOrderCreate | JSONResponse:
    order = await find_order(session, order_id)
    if order is None:
        return _not_found_response()
    if _is_yandex_order_payload(order.payload):
        yandex_order = YandexOrderCreate.model_validate(order.payload)
        content = _yandex_json(yandex_order)
        return JSONResponse(
            content=content,
            media_type="application/vnd.eats.order.v2+json",
        )
    return _response(order)


@router.get(
    "/order/{order_id}/status",
    response_model=OrderStatusResponse | YandexOrderStatusResponse,
)
async def get_order_status(
    order_id: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> OrderStatusResponse | YandexOrderStatusResponse | JSONResponse:
    order = await find_order(session, order_id)
    if order is None:
        return _not_found_response()
    if _is_yandex_order_payload(order.payload):
        updated_at = order.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return YandexOrderStatusResponse(
            status="NEW",
            comment="Заказ принят в тестовом режиме",
            updatedAt=updated_at,
        )
    return OrderStatusResponse(
        external_order_id=order.external_order_id,
        status=order.status,
        mode=order.mode,
        updated_at=order.updated_at,
    )
