from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.adapters.poster import PosterAPIError
from app.api.dependencies import require_access_token
from app.schemas.menu import MenuComposition
from app.services.poster_menu import PosterMenuService, PosterNotConfiguredError

MENU_CONTENT_TYPE = "application/vnd.eats.menu.composition.v2+json"


class YandexMenuResponse(JSONResponse):
    media_type = MENU_CONTENT_TYPE


router = APIRouter(tags=["menu"], dependencies=[Depends(require_access_token)])


def get_poster_menu_service(request: Request) -> PosterMenuService:
    return request.app.state.poster_menu_service


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
    menu_service: Annotated[PosterMenuService, Depends(get_poster_menu_service)],
) -> MenuComposition | JSONResponse:
    if restaurant_id != "pizzburg-main":
        return JSONResponse(
            status_code=404,
            content=[{"code": 404, "description": "Restaurant not found"}],
        )

    try:
        return await menu_service.get_menu()
    except PosterNotConfiguredError:
        return JSONResponse(
            status_code=503,
            content=[{"code": 503, "description": "Poster integration is not configured"}],
        )
    except PosterAPIError:
        return JSONResponse(
            status_code=502,
            content=[{"code": 502, "description": "Poster menu is temporarily unavailable"}],
        )
