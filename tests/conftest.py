from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def app(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}",
        auto_create_schema=True,
        oauth_client_id="test-client",
        oauth_client_secret="test-secret",
        jwt_secret="test-jwt-secret-that-is-long-enough-for-tests",
    )
    return create_app(settings)


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client


@pytest.fixture
async def token(client: AsyncClient) -> str:
    response = await client.post(
        "/security/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "test-client",
            "client_secret": "test-secret",
        },
    )
    return response.json()["access_token"]


@pytest.fixture
def order_payload() -> dict:
    return {
        "provider": "yandex",
        "external_order_id": "yandex-order-1001",
        "restaurant_id": "pizzburg-main",
        "currency": "KZT",
        "customer": {"name": "Test Customer", "phone": "+77000000000"},
        "delivery_address": {"full_address": "Almaty, Test street 1"},
        "items": [
            {
                "external_item_id": "pizza-1",
                "name": "Test Pizza",
                "quantity": 2,
                "unit_price": "2500.00",
                "modifiers": [],
            }
        ],
        "total": "5000.00",
        "comment": "Dry-run only",
        "created_at": "2026-08-07T10:00:00+05:00",
    }
