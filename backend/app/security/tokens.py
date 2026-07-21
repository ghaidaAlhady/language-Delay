"""Access-token (JWT) issuing/verification and opaque refresh-token handling.

Access tokens are short-lived, stateless JWTs. Refresh tokens are long-lived,
high-entropy opaque strings: the plaintext is returned to the client once and
never stored — only its SHA-256 hash is persisted, so a database leak does
not yield usable tokens. This keeps refresh tokens individually revocable
(logout) without needing to manage JWT blocklists.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import Settings
from app.core.errors import UnauthorizedError

ACCESS_TOKEN_TYPE = "access"
JWT_ALGORITHM = "HS256"


def create_access_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> str:
    """Return the user ID encoded in a valid access token, or raise."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid or expired access token.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid or expired access token.")
    return str(user_id)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
