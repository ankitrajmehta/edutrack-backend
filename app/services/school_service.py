"""
School service.

School row is created during auth/register. These endpoints retrieve and return
the existing profile — no creation logic needed here.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.school import School
from app.models.user import User
from app.schemas.school import SchoolResponse


async def register(db: AsyncSession, current_user: User) -> SchoolResponse:
    """
    'Register' endpoint — the School row already exists from auth/register.
    Fetches and returns the existing profile. Idempotent — no INSERT.
    """
    result = await db.execute(select(School).where(School.user_id == current_user.id))
    school = result.scalar_one_or_none()
    if school is None:
        raise NotFoundError("School profile", current_user.id)
    return SchoolResponse.model_validate(school)


async def get_profile(db: AsyncSession, current_user: User) -> SchoolResponse:
    """Return the authenticated school's profile."""
    result = await db.execute(select(School).where(School.user_id == current_user.id))
    school = result.scalar_one_or_none()
    if school is None:
        raise NotFoundError("School profile", current_user.id)
    return SchoolResponse.model_validate(school)
