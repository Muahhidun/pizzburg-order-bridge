import hmac
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.core.config import Settings


def authenticate_client(client_id: str, client_secret: str, settings: Settings) -> bool:
    expected_secret = settings.oauth_client_secret.get_secret_value()
    return hmac.compare_digest(client_id, settings.oauth_client_id) and hmac.compare_digest(
        client_secret, expected_secret
    )


def create_access_token(settings: Settings, scope: str = "orders") -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.token_ttl_seconds)
    payload = {
        "iss": settings.jwt_issuer,
        "sub": settings.oauth_client_id,
        "aud": settings.jwt_audience,
        "scope": scope,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, settings.token_ttl_seconds


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
