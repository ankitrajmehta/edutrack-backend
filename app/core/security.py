"""
Security utilities: JWT token creation/verification, password hashing.

JWT decisions (locked):
- sub claim: encoded as str(user.id), decoded as int(payload["sub"])
- access_token: 30-minute expiry
- refresh_token: 7-day expiry
- decode_token raises HTTP 401 — never returns None silently

bcrypt decisions (locked):
- passlib[bcrypt] with async wrapper
- bcrypt pinned >=4.1.2,<5.0.0
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt. Run in executor to avoid blocking event loop."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.
    - Expiry: ACCESS_TOKEN_EXPIRE_MINUTES (30 min default)
    - sub claim must be str(user.id)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token.
    - Expiry: REFRESH_TOKEN_EXPIRE_DAYS (7 days default)
    - Stored in DB with used=False; set used=True on first use.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises UnauthorizedError (HTTP 401) on invalid/expired token — never returns None.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("Token decode failed: %s", e)
        raise UnauthorizedError("Invalid or expired token")
