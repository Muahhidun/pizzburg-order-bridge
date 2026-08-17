import asyncio
import hashlib
from typing import Any

import httpx


class PosterAPIError(Exception):
    pass


class PosterClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://joinposter.com/api",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def _call(self, method: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    f"{self._base_url}/{method}",
                    params={"token": self._token},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PosterAPIError(f"Poster {method} request failed") from exc

        if not isinstance(payload, dict) or payload.get("error"):
            raise PosterAPIError(f"Poster {method} returned an API error")
        result = payload.get("response")
        if not isinstance(result, list):
            raise PosterAPIError(f"Poster {method} returned an unexpected response")
        return result

    async def get_categories(self) -> list[dict[str, Any]]:
        return await self._call("menu.getCategories")

    async def get_products(self) -> list[dict[str, Any]]:
        return await self._call("menu.getProducts")

    async def get_image_hashes(self, urls: list[str]) -> dict[str, str]:
        async def download(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
            response = await client.get(url)
            response.raise_for_status()
            return url, hashlib.sha1(response.content).hexdigest()

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                results = await asyncio.gather(
                    *(download(client, url) for url in dict.fromkeys(urls))
                )
        except httpx.HTTPError as exc:
            raise PosterAPIError("Poster product image request failed") from exc
        return dict(results)
