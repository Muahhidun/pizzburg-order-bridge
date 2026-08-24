import httpx

from app.api.routes import menu_images


async def test_menu_image_proxy_returns_joinposter_image(client, monkeypatch):
    async def fake_download(url: str) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"test-image",
            headers={"content-type": "image/jpeg"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(menu_images, "_download_image", fake_download)
    response = await client.get(
        "/menu-images/188",
        params={"source": "https://joinposter.com/upload/menu/product_188_original.jpeg"},
    )

    assert response.status_code == 200
    assert response.content == b"test-image"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "public, max-age=86400"


async def test_menu_image_proxy_rejects_unknown_hosts(client):
    response = await client.get(
        "/menu-images/188",
        params={"source": "https://example.com/not-allowed.jpeg"},
    )

    assert response.status_code == 400
