from pathlib import Path

import httpx

from app.api.routes import menu_images

HAM_BURGER_PHOTO = Path(menu_images.__file__).resolve().parents[2] / "assets" / "ham-burger.jpg"


async def test_missing_ham_burger_photo_is_available_without_external_download(client, monkeypatch):
    async def unexpected_download(url):
        raise AssertionError("Bundled photo must not depend on Poster")

    monkeypatch.setattr(menu_images, "_download_image", unexpected_download)
    response = await client.get("/menu-images/ham-burger.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == HAM_BURGER_PHOTO.read_bytes()
    assert response.content.startswith(b"\xff\xd8")


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
