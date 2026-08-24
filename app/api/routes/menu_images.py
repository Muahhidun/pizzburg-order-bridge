from typing import Annotated
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Response, status

router = APIRouter(tags=["menu images"])


async def _download_image(source: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        upstream = await client.get(source)
        upstream.raise_for_status()
        return upstream


@router.get("/menu-images/{product_id}", include_in_schema=False)
async def get_menu_image(
    product_id: str,
    source: Annotated[str, Query()],
) -> Response:
    parsed = urlparse(source)
    if (
        not product_id.isdigit()
        or parsed.scheme != "https"
        or parsed.hostname != "joinposter.com"
        or not parsed.path.startswith("/upload/")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid menu image source",
        )

    try:
        upstream = await _download_image(source)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Menu image is temporarily unavailable",
        ) from exc

    media_type = upstream.headers.get("content-type", "").split(";", 1)[0]
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Menu image source returned invalid content",
        )

    return Response(
        content=upstream.content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
