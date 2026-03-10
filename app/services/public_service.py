"""
Public service for unauthenticated API endpoints.

Provides: get_activity, get_public_ngos, get_public_programs.
Used by: app/api/public.py for public endpoint data fetching.
"""

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.ngo import NGO, NGOStatus
from app.models.program import Program, ProgramStatus
from app.schemas.public import (
    ActivityResponse,
    PublicNGOResponse,
    PublicProgramResponse,
)


async def get_activity(db: AsyncSession) -> List[ActivityResponse]:
    """
    Fetch all activity log entries, ordered by timestamp descending.
    Returns list of ActivityResponse with ISO 8601 formatted timestamps.
    """
    result = await db.execute(
        select(ActivityLog).order_by(ActivityLog.timestamp.desc())
    )
    logs = result.scalars().all()

    activities = []
    for log in logs:
        activities.append(
            ActivityResponse(
                type=log.type.value if hasattr(log.type, "value") else str(log.type),
                color=log.color or "gray",
                text=log.text,
                time=log.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                if log.timestamp
                else "",
            )
        )
    return activities


async def get_public_ngos(db: AsyncSession) -> List[PublicNGOResponse]:
    """
    Fetch all verified NGOs with public fields only.
    Returns list of PublicNGOResponse.
    """
    result = await db.execute(
        select(NGO).where(NGO.status == NGOStatus.verified).order_by(NGO.id)
    )
    ngos = result.scalars().all()

    public_ngos = []
    for ngo in ngos:
        public_ngos.append(
            PublicNGOResponse(
                id=ngo.id,
                name=ngo.name,
                location=ngo.location,
                status=ngo.status.value
                if hasattr(ngo.status, "value")
                else str(ngo.status),
                description=ngo.description or "",
                avatar=ngo.avatar,
                color=ngo.color,
                total_funded=ngo.total_funded,
                students_helped=ngo.students_helped,
                programs_count=ngo.programs_count,
                registered_date=ngo.registered_date.strftime("%Y-%m-%d")
                if ngo.registered_date
                else "",
            )
        )
    return public_ngos


async def get_public_programs(db: AsyncSession) -> List[PublicProgramResponse]:
    """
    Fetch all active programs with public fields only.
    Returns list of PublicProgramResponse.
    """
    result = await db.execute(
        select(Program)
        .where(Program.status == ProgramStatus.active)
        .order_by(Program.id)
    )
    programs = result.scalars().all()

    public_programs = []
    for program in programs:
        public_programs.append(
            PublicProgramResponse(
                id=program.id,
                ngo_id=program.ngo_id,
                name=program.name,
                description=program.description,
                status=program.status.value
                if hasattr(program.status, "value")
                else str(program.status),
                categories=program.categories or [],
                total_budget=program.total_budget,
                allocated=program.allocated,
                students_enrolled=program.students_enrolled,
                start_date=program.start_date.strftime("%Y-%m-%d")
                if program.start_date
                else None,
                end_date=program.end_date.strftime("%Y-%m-%d")
                if program.end_date
                else None,
            )
        )
    return public_programs
