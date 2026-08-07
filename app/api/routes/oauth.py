import base64
import binascii
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, status

from app.api.dependencies import get_request_settings
from app.core.config import Settings
from app.core.security import authenticate_client, create_access_token
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/security/oauth", tags=["security"])


def _basic_credentials(authorization: str | None) -> tuple[str | None, str | None]:
    if not authorization or not authorization.lower().startswith("basic "):
        return None, None
    try:
        raw = base64.b64decode(authorization.split(" ", 1)[1], validate=True).decode()
        return tuple(raw.split(":", 1)) if ":" in raw else (None, None)
    except (binascii.Error, UnicodeDecodeError):
        return None, None


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    grant_type: Annotated[str, Form()],
    settings: Annotated[Settings, Depends(get_request_settings)],
    authorization: Annotated[str | None, Header()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    scope: Annotated[str, Form()] = "orders",
) -> TokenResponse:
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_grant_type",
        )

    basic_id, basic_secret = _basic_credentials(authorization)
    resolved_id = basic_id or client_id or ""
    resolved_secret = basic_secret or client_secret or ""
    if not authenticate_client(resolved_id, resolved_secret, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_client",
            headers={"WWW-Authenticate": "Basic"},
        )

    token, expires_in = create_access_token(settings, scope)
    return TokenResponse(access_token=token, expires_in=expires_in, scope=scope)
