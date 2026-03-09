"""
FastAPI dependency injection hub.

All route handler dependencies live here. Never import concrete implementations
(mock_sui, database session) directly in route handlers.
"""

import logging
from typing import AsyncGenerator, Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db  # noqa: F401 — re-export
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.security import decode_token
from app.services.blockchain.base import BlockchainService
from app.services.blockchain.mock_sui import MockSuiService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_blockchain() -> BlockchainService:
    """
    Return the active BlockchainService implementation.
    To upgrade: change this return to SuiBlockchainService(). Zero other changes.
    """
    return MockSuiService()


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate Bearer token and return the authenticated User.
    Raises UnauthorizedError (HTTP 401) if token is missing, invalid, or expired.
    Raises UnauthorizedError (HTTP 401) if user is inactive.
    """
    # Import here to avoid circular import (models import database, dependencies imports models)
    from app.models.user import User

    if token is None:
        raise UnauthorizedError("Authentication required")

    payload = decode_token(token)  # raises 401 on invalid/expired

    # JWT sub is encoded as str(user.id), decoded as int
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise UnauthorizedError("Invalid token payload")

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    return user


def require_role(*roles: str) -> Callable:
    """
    RBAC dependency factory. Returns a FastAPI dependency that:
    1. Calls get_current_user() (validates token)
    2. Checks user.role is in the allowed roles list
    3. Raises ForbiddenError (HTTP 403) if role not allowed
    4. Returns the User object (ownership scoping is Phase 2 service-layer responsibility)

    Usage:
        current_user = Depends(require_role("ngo", "admin"))
        current_ngo_user = Depends(require_role("ngo"))
    """

    async def role_checker(
        current_user=Depends(get_current_user),
    ):
        if current_user.role.value not in roles:
            logger.warning(
                "Role check failed: user %d has role '%s', required one of %s",
                current_user.id,
                current_user.role.value,
                roles,
            )
            raise ForbiddenError(
                f"Role '{current_user.role.value}' does not have access. Required: {list(roles)}"
            )
        return current_user

    return role_checker
