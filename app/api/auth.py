"""
Authentication endpoints.

All handlers: validate → call one service method → return result.
No business logic in handlers.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
    MessageResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user (ngo/donor/school/student). Returns JWT tokens on success."""
    return await auth_service.register(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password. Returns JWT access token (30min) and refresh token (7d)."""
    return await auth_service.login(db, data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token. Invalidates the used refresh token."""
    return await auth_service.refresh(db, data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    data: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Invalidate the submitted refresh token. Subsequent use returns 401."""
    await auth_service.logout(db, data.refresh_token)


@router.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the current user's role-specific profile. Flat object matching mock.js shape."""
    return await auth_service.get_profile(db, current_user)
