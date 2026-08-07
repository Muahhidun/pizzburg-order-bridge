from fastapi import APIRouter, Depends

from app.api.dependencies import require_access_token
from app.schemas.restaurant import RestaurantResponse

router = APIRouter(tags=["restaurants"], dependencies=[Depends(require_access_token)])


@router.get("/restaurants", response_model=list[RestaurantResponse])
async def list_restaurants() -> list[RestaurantResponse]:
    return [
        RestaurantResponse(
            id="pizzburg-main",
            name="Pizzburg",
            active=True,
            mode="dry-run",
        )
    ]
