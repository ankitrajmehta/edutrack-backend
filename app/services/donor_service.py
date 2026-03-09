"""
Donor service.

Read-only browsing of verified NGOs, active programs, and active students.
No ownership scoping — donors browse public-facing verified/active records.
No activity logging — read operations don't write activity entries.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ngo import NGO, NGOStatus
from app.models.program import Program, ProgramStatus
from app.models.student import Student, StudentStatus
from app.schemas.ngo import NGOResponse
from app.schemas.program import ProgramResponse
from app.schemas.student import StudentResponse


async def browse_ngos(db: AsyncSession) -> list[NGOResponse]:
    """Return all verified NGOs."""
    result = await db.execute(select(NGO).where(NGO.status == NGOStatus.verified))
    return [NGOResponse.model_validate(ngo) for ngo in result.scalars().all()]


async def browse_programs(db: AsyncSession) -> list[ProgramResponse]:
    """Return all active programs."""
    result = await db.execute(
        select(Program).where(Program.status == ProgramStatus.active)
    )
    return [ProgramResponse.model_validate(p) for p in result.scalars().all()]


async def browse_students(db: AsyncSession) -> list[StudentResponse]:
    """Return all active students."""
    result = await db.execute(
        select(Student).where(Student.status == StudentStatus.active)
    )
    return [StudentResponse.model_validate(s) for s in result.scalars().all()]
