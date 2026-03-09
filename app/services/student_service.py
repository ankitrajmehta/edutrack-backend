"""
Student service.

Student users browse programs and submit/view their own applications.
Application ownership tracked via submitted_by_user_id (set at submission, used for filtering).

Note: Student auth users do NOT have a Student ORM row until enrolled by an NGO.
Applications are linked to the submitting user via submitted_by_user_id FK.
"""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ConflictError
from app.models.application import ScholarshipApplication, ApplicationStatus
from app.models.program import Program, ProgramStatus
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationResponse
from app.schemas.program import ProgramResponse


async def browse_programs(db: AsyncSession) -> list[ProgramResponse]:
    """Return all active scholarship programs — no role filter needed for browsing."""
    result = await db.execute(
        select(Program).where(Program.status == ProgramStatus.active)
    )
    return [ProgramResponse.model_validate(p) for p in result.scalars().all()]


async def submit_application(
    db: AsyncSession, data: ApplicationCreate, current_user: User
) -> ApplicationResponse:
    """
    Submit a scholarship application.
    submitted_by_user_id is set to current_user.id for ownership filtering in list_own_applications.
    """
    # Verify the target program exists and is active
    program = await db.get(Program, data.program_id)
    if program is None:
        raise NotFoundError("Program", data.program_id)
    if program.status != ProgramStatus.active:
        raise ConflictError(
            "program", f"Program {data.program_id} is not accepting applications"
        )

    application = ScholarshipApplication(
        program_id=data.program_id,
        student_name=data.student_name,
        age=data.age,
        grade=data.grade,
        school_name=data.school_name,
        school_district=data.school_district,
        guardian_name=data.guardian_name,
        guardian_relation=data.guardian_relation,
        guardian_contact=data.guardian_contact,
        reason=data.reason,
        status=ApplicationStatus.pending,
        applied_date=datetime.now(timezone.utc).replace(tzinfo=None),
        submitted_by_user_id=current_user.id,  # CRITICAL: set for ownership filtering
    )
    db.add(application)
    await db.commit()
    return ApplicationResponse.model_validate(application)


async def list_own_applications(
    db: AsyncSession, current_user: User
) -> list[ApplicationResponse]:
    """
    Return applications submitted by this user.
    Filters by submitted_by_user_id == current_user.id (RBAC-04 ownership scoping).
    """
    result = await db.execute(
        select(ScholarshipApplication).where(
            ScholarshipApplication.submitted_by_user_id == current_user.id
        )
    )
    return [ApplicationResponse.model_validate(a) for a in result.scalars().all()]
