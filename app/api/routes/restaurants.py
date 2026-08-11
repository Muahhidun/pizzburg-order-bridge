from fastapi import APIRouter, Depends

from app.api.dependencies import require_access_token
from app.schemas.restaurant import RestaurantList, RestaurantPlace

router = APIRouter(tags=["restaurants"], dependencies=[Depends(require_access_token)])


@router.get("/restaurants", response_model=RestaurantList)
async def list_restaurants() -> RestaurantList:
    return RestaurantList(
        places=[
            RestaurantPlace(
                id="pizzburg-main",
                title="PizzBurg",
                address="Казахстан, Экибастуз, ул. Ауэзова, 47Б, ТРЦ MaxiMall",
            )
        ]
    )
