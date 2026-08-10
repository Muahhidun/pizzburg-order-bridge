from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import require_access_token
from app.schemas.menu import MenuCategory, MenuComposition, MenuItem

MENU_CONTENT_TYPE = "application/vnd.eats.menu.composition.v2+json"


class YandexMenuResponse(JSONResponse):
    media_type = MENU_CONTENT_TYPE


router = APIRouter(tags=["menu"], dependencies=[Depends(require_access_token)])


@router.get(
    "/menu/{restaurant_id}/composition",
    response_model=MenuComposition,
    response_model_by_alias=True,
    response_class=YandexMenuResponse,
    responses={
        404: {
            "description": "Restaurant not found",
            "content": {
                "application/json": {
                    "example": [{"code": 404, "description": "Restaurant not found"}]
                }
            },
        }
    },
)
async def get_menu_composition(
    restaurant_id: str,
) -> MenuComposition | JSONResponse:
    if restaurant_id != "pizzburg-main":
        return JSONResponse(
            status_code=404,
            content=[{"code": 404, "description": "Restaurant not found"}],
        )

    return MenuComposition(
        categories=[
            MenuCategory(
                id="test-pizzas",
                name="Тестовые пиццы",
                sort_order=10,
            )
        ],
        items=[
            MenuItem(
                id="test-pizza-margherita",
                category_id="test-pizzas",
                name="[ТЕСТ] Пицца Маргарита",
                description="Тестовая позиция для проверки интеграции Яндекс Еды",
                price=2500.0,
                measure=500,
                measure_unit="g",
                sort_order=10,
            ),
            MenuItem(
                id="test-pizza-pepperoni",
                category_id="test-pizzas",
                name="[ТЕСТ] Пицца Пепперони",
                description="Тестовая позиция для проверки интеграции Яндекс Еды",
                price=3000.0,
                measure=550,
                measure_unit="g",
                sort_order=20,
            ),
        ],
        last_change="2026-08-10T16:00:00.000000+05:00",
    )
