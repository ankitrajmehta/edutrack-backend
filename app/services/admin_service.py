"""
Admin service.

Provides: get_stats, list_ngos, update_ngo_status, get_blacklist, update_student_status.
All mutating methods call activity_service.log() BEFORE db.commit() for atomicity.
"""

from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.ngo import NGO, NGOStatus
from app.models.student import Student, StudentStatus
from app.models.donation import Donation
from app.models.program import Program
from app.models.school import School
from app.schemas.admin import AdminStatsResponse, BlacklistResponse
from app.schemas.ngo import NGOResponse
from app.schemas.student import StudentResponse
from app.services import activity_service


async def get_stats(db: AsyncSession) -> AdminStatsResponse:
    """Aggregate platform statistics via COUNT/SUM queries."""
    total_donations = (
        await db.execute(select(func.coalesce(func.sum(Donation.amount), 0.0)))
    ).scalar_one()
    total_students = (await db.execute(select(func.count(Student.id)))).scalar_one()
    total_ngos = (await db.execute(select(func.count(NGO.id)))).scalar_one()
    total_programs = (await db.execute(select(func.count(Program.id)))).scalar_one()
    total_schools = (await db.execute(select(func.count(School.id)))).scalar_one()
    # funds_allocated: sum of all NGO.total_funded (funds sent to NGO wallets)
    funds_allocated = (
        await db.execute(select(func.coalesce(func.sum(NGO.total_funded), 0.0)))
    ).scalar_one()
    # funds_utilized: sum of all Student.total_received (funds actually delivered to students)
    funds_utilized = (
        await db.execute(select(func.coalesce(func.sum(Student.total_received), 0.0)))
    ).scalar_one()

    return AdminStatsResponse(
        total_donations=float(total_donations),
        total_students=int(total_students),
        total_ngos=int(total_ngos),
        total_programs=int(total_programs),
        total_schools=int(total_schools),
        funds_allocated=float(funds_allocated),
        funds_utilized=float(funds_utilized),
    )


async def list_ngos(
    db: AsyncSession, status: Optional[str] = None
) -> list[NGOResponse]:
    """List NGOs, optionally filtered by status string."""
    q = select(NGO)
    if status:
        try:
            q = q.where(NGO.status == NGOStatus(status))
        except ValueError:
            # Invalid status string — return empty list (graceful degradation)
            return []
    result = await db.execute(q)
    ngos = result.scalars().all()
    return [NGOResponse.model_validate(ngo) for ngo in ngos]


async def update_ngo_status(
    db: AsyncSession, ngo_id: int, new_status: str, actor_id: int
) -> NGOResponse:
    """
    Mutate NGO.status. Valid transitions: verify, reject, blacklist, restore.
    Writes activity log BEFORE committing (atomicity requirement).
    """
    result = await db.execute(select(NGO).where(NGO.id == ngo_id))
    ngo = result.scalar_one_or_none()
    if ngo is None:
        raise NotFoundError("NGO", ngo_id)

    # Map action name to NGOStatus enum value and log type/text
    action_map = {
        "verify": (NGOStatus.verified, "verify", f"NGO '{ngo.name}' verified"),
        "reject": (NGOStatus.rejected, "verify", f"NGO '{ngo.name}' rejected"),
        "blacklist": (
            NGOStatus.blacklisted,
            "blacklist",
            f"NGO '{ngo.name}' blacklisted",
        ),
        "restore": (
            NGOStatus.pending,
            "verify",
            f"NGO '{ngo.name}' restored to pending",
        ),
    }
    if new_status not in action_map:
        raise ValueError(f"Unknown action: {new_status}")

    status_value, log_type, log_text = action_map[new_status]
    ngo.status = status_value

    # Log BEFORE commit — atomicity requirement
    await activity_service.log(db, log_type, log_text, actor_id)
    await db.commit()

    return NGOResponse.model_validate(ngo)


async def get_blacklist(db: AsyncSession) -> BlacklistResponse:
    """Return all blacklisted NGOs and students."""
    ngo_result = await db.execute(
        select(NGO).where(NGO.status == NGOStatus.blacklisted)
    )
    blacklisted_ngos = [
        NGOResponse.model_validate(n) for n in ngo_result.scalars().all()
    ]

    student_result = await db.execute(
        select(Student).where(Student.status == StudentStatus.blacklisted)
    )
    blacklisted_students = [
        StudentResponse.model_validate(s) for s in student_result.scalars().all()
    ]

    return BlacklistResponse(ngos=blacklisted_ngos, students=blacklisted_students)


async def update_student_status(
    db: AsyncSession, student_id: int, action: str, actor_id: int
) -> StudentResponse:
    """
    Blacklist or restore a student.
    action: "blacklist" | "restore"
    """
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student", student_id)

    if action == "blacklist":
        student.status = StudentStatus.blacklisted
        log_text = f"Student '{student.name}' blacklisted"
        log_type = "blacklist"
    else:  # restore
        student.status = StudentStatus.active
        log_text = f"Student '{student.name}' restored"
        log_type = "verify"

    # Log BEFORE commit — atomicity requirement
    await activity_service.log(db, log_type, log_text, actor_id)
    await db.commit()

    return StudentResponse.model_validate(student)
