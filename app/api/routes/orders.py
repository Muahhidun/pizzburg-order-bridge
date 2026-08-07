from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session, require_access_token
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusResponse
from app.services.orders import DuplicateOrderConflictError, find_order, save_dry_run_order

router = APIRouter(tags=["orders"], dependencies=[Depends(require_access_token)])


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


@router.post("/order", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: OrderCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderResponse:
    try:
        order, duplicate = await save_dry_run_order(session, request)
    except DuplicateOrderConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order ID already exists with different content",
        ) from exc
    if duplicate:
        response.status_code = status.HTTP_200_OK
    return _response(order, duplicate)


@router.get("/order/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> OrderResponse:
    order = await find_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _response(order)


@router.get("/order/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> OrderStatusResponse:
    order = await find_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderStatusResponse(
        external_order_id=order.external_order_id,
        status=order.status,
        mode=order.mode,
        updated_at=order.updated_at,
    )
