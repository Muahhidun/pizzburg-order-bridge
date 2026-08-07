from app.core.config import Settings


def test_railway_postgres_url_uses_async_driver():
    settings = Settings(database_url="postgresql://user:password@host:5432/database")

    assert settings.database_url == "postgresql+asyncpg://user:password@host:5432/database"
