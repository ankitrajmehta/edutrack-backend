"""
Authentication service.

Implements: register, login, refresh, logout, get_profile.
All DB writes happen here — route handlers never call db.commit() directly.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, RefreshToken, UserRole
from app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    LoginRequest,
    NGOProfileResponse,
    DonorProfileResponse,
    SchoolProfileResponse,
    StudentProfileResponse,
    AdminProfileResponse,
)

logger = logging.getLogger(__name__)


async def register(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    """
    Register a new user + role-specific profile row.
    Raises ConflictError if email already exists.
    Returns TokenResponse with access + refresh tokens.
    """
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("email", data.email)

    # Hash password — bcrypt is CPU-intensive; run in thread pool to avoid blocking event loop
    hashed = await asyncio.get_event_loop().run_in_executor(
        None, hash_password, data.password
    )

    # Create User row
    user = User(
        email=data.email,
        hashed_password=hashed,
        role=UserRole(data.role),
        is_active=True,
    )
    db.add(user)
    await db.flush()  # get user.id without committing

    # Create role-specific profile row
    await _create_profile(db, user, data)

    await db.commit()

    # Issue tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    # Store refresh token in DB
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    refresh_token_row = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        used=False,
        expires_at=expires_at,
    )
    db.add(refresh_token_row)
    await db.commit()

    logger.info(
        "User registered: id=%d email=%s role=%s", user.id, user.email, user.role
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


async def _create_profile(db: AsyncSession, user: User, data: RegisterRequest) -> None:
    """Create the role-specific profile row for a new user."""
    if user.role == UserRole.ngo:
        from app.models.ngo import NGO

        profile = NGO(
            user_id=user.id,
            name=data.name,
            location=data.location or "",
            description=data.description,
        )
        db.add(profile)

    elif user.role == UserRole.donor:
        from app.models.donor import Donor

        profile = Donor(user_id=user.id, name=data.name, email=data.email)
        db.add(profile)

    elif user.role == UserRole.school:
        from app.models.school import School

        profile = School(user_id=user.id, name=data.name, location=data.location)
        db.add(profile)

    elif user.role == UserRole.student:
        from app.models.student import Student

        profile = Student(user_id=user.id, name=data.name, location=data.location)
        db.add(profile)
    # admin: no separate profile row


async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return tokens.
    Raises UnauthorizedError on bad credentials or inactive user.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("Login failed: email %s not found", data.email)
        raise UnauthorizedError("Invalid email or password")

    # verify_password is CPU-intensive — run in thread pool
    password_valid = await asyncio.get_event_loop().run_in_executor(
        None, verify_password, data.password, user.hashed_password
    )
    if not password_valid:
        logger.warning("Login failed: wrong password for %s", data.email)
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    # Store new refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    refresh_token_row = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        used=False,
        expires_at=expires_at,
    )
    db.add(refresh_token_row)
    await db.commit()

    logger.info("User logged in: id=%d email=%s", user.id, user.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


async def refresh(db: AsyncSession, refresh_token_str: str) -> TokenResponse:
    """
    Issue new access token from valid refresh token.
    Raises UnauthorizedError if token is invalid, used, or expired.
    Sets used=True on the refresh token after use (prevents race-condition reuse).
    """
    payload = decode_token(refresh_token_str)  # raises 401 if invalid/expired

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Not a refresh token")

    # Look up in DB — reject if already used
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    token_row = result.scalar_one_or_none()

    if token_row is None:
        raise UnauthorizedError("Refresh token not found")
    if token_row.used:
        logger.warning(
            "Attempted reuse of refresh token for user_id=%d", token_row.user_id
        )
        raise UnauthorizedError("Refresh token already used")
    if token_row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token expired")

    # Mark as used before issuing new token (prevents race)
    token_row.used = True
    await db.commit()

    # Issue new tokens
    user_id = int(payload["sub"])
    access_token = create_access_token({"sub": str(user_id)})
    new_refresh_str = create_refresh_token({"sub": str(user_id)})

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    new_refresh_row = RefreshToken(
        user_id=user_id,
        token=new_refresh_str,
        used=False,
        expires_at=expires_at,
    )
    db.add(new_refresh_row)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_str)


async def logout(db: AsyncSession, refresh_token_str: str) -> None:
    """
    Invalidate a refresh token.
    Sets used=True; subsequent use of this token returns 401.
    """
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    token_row = result.scalar_one_or_none()

    if token_row is not None and not token_row.used:
        token_row.used = True
        await db.commit()
        logger.info("User logged out: user_id=%d", token_row.user_id)


async def get_profile(db: AsyncSession, user: User):
    """
    Return the user's merged flat profile (user fields + role-specific fields).
    Shape matches mock.js exactly — flat object, no nested {user, profile} envelope.
    Admin has no separate profile model — returns just User fields.
    """
    if user.role == UserRole.ngo:
        from app.models.ngo import NGO

        result = await db.execute(select(NGO).where(NGO.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            # Fallback to base user response
            return AdminProfileResponse.model_validate(user)
        return NGOProfileResponse(
            id=user.id,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at,
            name=profile.name,
            location=profile.location,
            status=profile.status.value if profile.status else None,
            description=profile.description,
            avatar=profile.avatar,
            color=profile.color,
            total_funded=profile.total_funded,
            students_helped=profile.students_helped,
            programs_count=profile.programs_count,
            registered_date=profile.registered_date,
        )

    elif user.role == UserRole.donor:
        from app.models.donor import Donor

        result = await db.execute(select(Donor).where(Donor.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            return AdminProfileResponse.model_validate(user)
        return DonorProfileResponse(
            id=user.id,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at,
            name=profile.name,
            total_donated=profile.total_donated,
            donations_count=profile.donations_count,
        )

    elif user.role == UserRole.school:
        from app.models.school import School

        result = await db.execute(select(School).where(School.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            return AdminProfileResponse.model_validate(user)
        return SchoolProfileResponse(
            id=user.id,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at,
            name=profile.name,
            location=profile.location,
            status=profile.status.value if profile.status else None,
            students_in_programs=profile.students_in_programs,
            total_invoiced=profile.total_invoiced,
        )

    elif user.role == UserRole.student:
        # Student records are created by NGO (Phase 2) — no user_id FK on Student in Phase 1
        # Return generic user fields for now; full student profile available in Phase 2
        return StudentProfileResponse(
            id=user.id,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at,
            name=user.email.split("@")[0],  # placeholder until student record exists
            wallet_balance=0.0,
            total_received=0.0,
        )

    else:
        # admin role — just user fields
        return AdminProfileResponse.model_validate(user)
