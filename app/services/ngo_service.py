"""
NGO service.

All methods scoped to the authenticated NGO's records.
Ownership check pattern: if record.ngo_id != ngo.id: raise ForbiddenError(...)
_create_student() is the shared helper used by BOTH direct registration and accept-application.
"""

import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ForbiddenError,
    ConflictError,
    AppValidationError,
)
from app.models.application import ScholarshipApplication, ApplicationStatus
from app.models.ngo import NGO
from app.models.program import Program
from app.models.student import Student
from app.models.invoice import Invoice, InvoiceStatus
from app.models.allocation import Allocation
from app.schemas.application import ApplicationResponse
from app.schemas.ngo import NGOStatsResponse
from app.schemas.program import ProgramCreate, ProgramUpdate, ProgramResponse
from app.schemas.student import StudentCreate, StudentResponse
from app.schemas.invoice import InvoiceResponse
from app.schemas.allocation import AllocationCreate, AllocationResponse
from app.services import activity_service
from app.services.blockchain.base import BlockchainService


# ─── Private helpers ───────────────────────────────────────────────────────────


async def _generate_scholarship_id(db: AsyncSession) -> str:
    """Generate unique EDU-YYYY-XXXXX, retry on collision (max 10 attempts)."""
    year = datetime.now(timezone.utc).year
    for _ in range(10):
        number = str(random.randint(0, 99999)).zfill(5)
        candidate = f"EDU-{year}-{number}"
        result = await db.execute(
            select(Student).where(Student.scholarship_id == candidate)
        )
        if result.scalar_one_or_none() is None:
            return candidate
    raise ConflictError("scholarship_id", "generation failed after 10 retries")


async def _create_student(
    db: AsyncSession,
    ngo: NGO,
    name: str,
    age: Optional[int],
    school: Optional[str],
    grade: Optional[str],
    guardian: Optional[str],
    location: Optional[str],
    program_id: int,
    blockchain: BlockchainService,
    actor_id: int,
) -> Student:
    """
    Shared student creation helper used by BOTH direct registration and accept-application.

    Transaction flow:
      1. Generate scholarship ID (SELECT with retry)
      2. INSERT Student row
      3. db.flush() — get student.id without committing
      4. blockchain.create_wallet(student.id) — if fails, session rolls back on caller's exception
      5. activity_service.log() — BEFORE commit
      6. db.commit() — atomic with log entry
    """
    scholarship_id = await _generate_scholarship_id(db)
    student = Student(
        ngo_id=ngo.id,
        program_id=program_id,
        name=name,
        age=age,
        school=school,
        grade=grade,
        guardian=guardian,
        location=location,
        scholarship_id=scholarship_id,
    )
    db.add(student)
    await db.flush()  # get student.id for blockchain call

    # Create blockchain wallet — atomic: if this raises, student row rolls back (only flushed, not committed)
    wallet_result = await blockchain.create_wallet(str(student.id))
    student.wallet_address = wallet_result.wallet_address

    # Fetch program name for activity log text
    program = await db.get(Program, program_id)
    program_name = program.name if program else "Unknown Program"

    # Log BEFORE commit — atomicity requirement
    await activity_service.log(
        db,
        "allocation",
        f"Student '{name}' enrolled in {program_name}",
        actor_id,
    )
    await db.commit()
    return student


# ─── Public service functions ──────────────────────────────────────────────────


async def get_dashboard(db: AsyncSession, ngo: NGO) -> NGOStatsResponse:
    """Return NGO-scoped dashboard stats."""
    return NGOStatsResponse(
        programs_count=ngo.programs_count,
        students_helped=ngo.students_helped,
        funds_allocated=ngo.total_funded,
    )


async def create_program(
    db: AsyncSession, data: ProgramCreate, ngo: NGO, actor_id: int
) -> ProgramResponse:
    program = Program(
        ngo_id=ngo.id,
        name=data.name,
        description=data.description,
        categories=data.categories,
        total_budget=data.total_budget,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(program)
    await db.flush()  # get program.id

    # Update NGO programs_count counter
    ngo.programs_count = ngo.programs_count + 1

    await activity_service.log(
        db,
        "program",
        f"Program '{program.name}' created by {ngo.name}",
        actor_id,
    )
    await db.commit()
    return ProgramResponse.model_validate(program)


async def list_programs(db: AsyncSession, ngo: NGO) -> list[ProgramResponse]:
    result = await db.execute(select(Program).where(Program.ngo_id == ngo.id))
    return [ProgramResponse.model_validate(p) for p in result.scalars().all()]


async def get_program(db: AsyncSession, program_id: int, ngo: NGO) -> ProgramResponse:
    result = await db.execute(select(Program).where(Program.id == program_id))
    program = result.scalar_one_or_none()
    if program is None:
        raise NotFoundError("Program", program_id)
    if program.ngo_id != ngo.id:
        raise ForbiddenError("You do not own this program")
    return ProgramResponse.model_validate(program)


async def update_program(
    db: AsyncSession, program_id: int, data: ProgramUpdate, ngo: NGO, actor_id: int
) -> ProgramResponse:
    result = await db.execute(select(Program).where(Program.id == program_id))
    program = result.scalar_one_or_none()
    if program is None:
        raise NotFoundError("Program", program_id)
    if program.ngo_id != ngo.id:
        raise ForbiddenError("You do not own this program")

    if data.name is not None:
        program.name = data.name
    if data.description is not None:
        program.description = data.description
    if data.categories is not None:
        program.categories = data.categories
    if data.total_budget is not None:
        program.total_budget = data.total_budget
    if data.status is not None:
        from app.models.program import ProgramStatus

        program.status = ProgramStatus(data.status)
    if data.start_date is not None:
        program.start_date = data.start_date
    if data.end_date is not None:
        program.end_date = data.end_date

    await db.commit()
    return ProgramResponse.model_validate(program)


async def delete_program(
    db: AsyncSession, program_id: int, ngo: NGO, actor_id: int
) -> None:
    """Delete a program owned by the authenticated NGO."""
    result = await db.execute(select(Program).where(Program.id == program_id))
    program = result.scalar_one_or_none()
    if program is None:
        raise NotFoundError("Program", program_id)
    if program.ngo_id != ngo.id:
        raise ForbiddenError("You do not own this program")

    await activity_service.log(
        db,
        "program",
        f"Program '{program.name}' deleted by {ngo.name}",
        actor_id,
    )
    await db.delete(program)
    await db.commit()


async def register_student(
    db: AsyncSession,
    data: StudentCreate,
    ngo: NGO,
    blockchain: BlockchainService,
    actor_id: int,
) -> StudentResponse:
    """Direct NGO student registration path."""
    student = await _create_student(
        db=db,
        ngo=ngo,
        name=data.name,
        age=data.age,
        school=data.school,
        grade=data.grade,
        guardian=data.guardian,
        location=data.location,
        program_id=data.program_id,
        blockchain=blockchain,
        actor_id=actor_id,
    )
    # Update NGO students_helped counter (ngo already in session, commit already done by _create_student)
    # Re-fetch ngo to avoid stale state after commit
    await db.refresh(ngo)
    ngo.students_helped = ngo.students_helped + 1
    await db.commit()
    return StudentResponse.model_validate(student)


async def list_students(db: AsyncSession, ngo: NGO) -> list[StudentResponse]:
    result = await db.execute(select(Student).where(Student.ngo_id == ngo.id))
    return [StudentResponse.model_validate(s) for s in result.scalars().all()]


async def get_student(db: AsyncSession, student_id: int, ngo: NGO) -> StudentResponse:
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student", student_id)
    if student.ngo_id != ngo.id:
        raise ForbiddenError("You do not own this student")
    return StudentResponse.model_validate(student)


async def list_applications(db: AsyncSession, ngo: NGO) -> list[ApplicationResponse]:
    """List pending applications for this NGO's programs."""
    # Get all program IDs for this NGO
    prog_result = await db.execute(select(Program.id).where(Program.ngo_id == ngo.id))
    program_ids = [row[0] for row in prog_result.fetchall()]
    if not program_ids:
        return []

    result = await db.execute(
        select(ScholarshipApplication).where(
            ScholarshipApplication.program_id.in_(program_ids),
            ScholarshipApplication.status == ApplicationStatus.pending,
        )
    )
    return [ApplicationResponse.model_validate(a) for a in result.scalars().all()]


async def accept_application(
    db: AsyncSession,
    application_id: int,
    ngo: NGO,
    blockchain: BlockchainService,
    actor_id: int,
) -> StudentResponse:
    """Accept application → auto-create Student using same _create_student() helper."""
    result = await db.execute(
        select(ScholarshipApplication).where(
            ScholarshipApplication.id == application_id
        )
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise NotFoundError("Application", application_id)

    # Verify this application belongs to an NGO-owned program
    prog_result = await db.execute(select(Program).where(Program.id == app.program_id))
    program = prog_result.scalar_one_or_none()
    if program is None or program.ngo_id != ngo.id:
        raise ForbiddenError("Application does not belong to your programs")

    # Field mapping: application → student (per CONTEXT.md Application → Student rules)
    student = await _create_student(
        db=db,
        ngo=ngo,
        name=app.student_name,
        age=app.age,
        school=app.school_name,
        grade=app.grade,
        guardian=app.guardian_name,
        location=app.school_district,
        program_id=app.program_id,
        blockchain=blockchain,
        actor_id=actor_id,
    )

    # Update application status AFTER student creation (_create_student already committed)
    # Re-fetch application to get fresh state post-commit
    await db.refresh(app)
    app.status = ApplicationStatus.accepted

    # Log accept action
    await activity_service.log(
        db,
        "program",
        f"Application from '{app.student_name}' accepted into '{program.name}'",
        actor_id,
    )
    await db.commit()

    return StudentResponse.model_validate(student)


async def reject_application(
    db: AsyncSession, application_id: int, ngo: NGO, reason: str, actor_id: int
) -> ApplicationResponse:
    """Reject application, store rejection_reason."""
    result = await db.execute(
        select(ScholarshipApplication).where(
            ScholarshipApplication.id == application_id
        )
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise NotFoundError("Application", application_id)

    # Verify ownership
    prog_result = await db.execute(select(Program).where(Program.id == app.program_id))
    program = prog_result.scalar_one_or_none()
    if program is None or program.ngo_id != ngo.id:
        raise ForbiddenError("Application does not belong to your programs")

    app.status = ApplicationStatus.rejected
    app.rejection_reason = reason

    await activity_service.log(
        db,
        "program",
        f"Application from '{app.student_name}' rejected",
        actor_id,
    )
    await db.commit()
    return ApplicationResponse.model_validate(app)


# ─── Invoice & Allocation functions (NGO-08 through NGO-11) ───────────────────────


async def list_invoices(db: AsyncSession, ngo: NGO) -> list[InvoiceResponse]:
    """NGO-08: List invoices for this NGO only (scoped by ngo_id)."""
    result = await db.execute(
        select(Invoice).where(Invoice.ngo_id == ngo.id).order_by(Invoice.id.desc())
    )
    return [InvoiceResponse.model_validate(i) for i in result.scalars().all()]


async def approve_invoice(
    db: AsyncSession,
    invoice_id: int,
    ngo: NGO,
    blockchain: BlockchainService,
    actor_id: int,
) -> InvoiceResponse:
    """NGO-09: Approve invoice — blockchain.settle_invoice() FIRST, then mutate, then commit."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise NotFoundError("Invoice", invoice_id)
    if invoice.ngo_id != ngo.id:
        raise ForbiddenError("Invoice does not belong to your NGO")
    if invoice.status != InvoiceStatus.pending:
        raise AppValidationError(f"Invoice is already {invoice.status.value}")

    # Blockchain FIRST — no commit until tx_hash confirmed
    tx = await blockchain.settle_invoice(
        str(ngo.id), str(invoice.school_id), str(invoice.id), invoice.amount
    )
    invoice.status = InvoiceStatus.approved
    invoice.tx_hash = tx.tx_hash
    invoice.approved_date = datetime.now(timezone.utc)

    await activity_service.log(
        db,
        "invoice",
        f"Invoice #{invoice.id} from '{invoice.school_name}' approved by {ngo.name}",
        actor_id,
    )
    await db.commit()
    await db.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


async def reject_invoice(
    db: AsyncSession,
    invoice_id: int,
    ngo: NGO,
    actor_id: int,
    reason: Optional[str] = None,
) -> InvoiceResponse:
    """NGO-09: Reject invoice — no blockchain call, status → rejected."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise NotFoundError("Invoice", invoice_id)
    if invoice.ngo_id != ngo.id:
        raise ForbiddenError("Invoice does not belong to your NGO")
    if invoice.status != InvoiceStatus.pending:
        raise AppValidationError(f"Invoice is already {invoice.status.value}")

    invoice.status = InvoiceStatus.rejected

    await activity_service.log(
        db,
        "invoice",
        f"Invoice #{invoice.id} from '{invoice.school_name}' rejected by {ngo.name}",
        actor_id,
    )
    await db.commit()
    await db.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


async def create_allocation(
    db: AsyncSession,
    data: AllocationCreate,
    ngo: NGO,
    blockchain: BlockchainService,
    actor_id: int,
) -> AllocationResponse:
    """NGO-10: Allocate funds — blockchain.allocate_funds() FIRST, then insert Allocation, update student wallet, then commit."""
    if not data.student_id and not data.program_id:
        raise AppValidationError("Either studentId or programId must be provided")

    # Resolve target for blockchain call and activity log
    target_name = f"{'student' if data.student_id else 'program'} #{data.student_id or data.program_id}"

    # Blockchain FIRST — allocate_funds(ngo_id, program_id, student_id, amount)
    tx = await blockchain.allocate_funds(
        str(ngo.id),
        str(data.program_id or 0),
        str(data.student_id or 0),
        data.amount,
    )

    allocation = Allocation(
        ngo_id=ngo.id,
        student_id=data.student_id,
        program_id=data.program_id,
        amount=data.amount,
        tx_hash=tx.tx_hash,
    )
    db.add(allocation)

    # Update student wallet balance if targeting a student
    if data.student_id:
        student_result = await db.execute(
            select(Student).where(Student.id == data.student_id)
        )
        student = student_result.scalar_one_or_none()
        if student is not None:
            student.wallet_balance = student.wallet_balance + data.amount
            student.total_received = student.total_received + data.amount
            target_name = f"student '{student.name}'"

    # Update program allocated counter if targeting a program
    elif data.program_id:
        prog_result = await db.execute(
            select(Program).where(Program.id == data.program_id)
        )
        program = prog_result.scalar_one_or_none()
        if program is not None:
            program.allocated = program.allocated + data.amount
            target_name = f"program '{program.name}'"

    await activity_service.log(
        db,
        "allocation",
        f"{ngo.name} allocated ${data.amount:,.2f} to {target_name}",
        actor_id,
    )
    await db.commit()
    await db.refresh(allocation)
    return AllocationResponse.model_validate(allocation)


async def list_allocations(db: AsyncSession, ngo: NGO) -> list[AllocationResponse]:
    """NGO-11: List this NGO's allocations (scoped by ngo_id)."""
    result = await db.execute(
        select(Allocation)
        .where(Allocation.ngo_id == ngo.id)
        .order_by(Allocation.id.desc())
    )
    return [AllocationResponse.model_validate(a) for a in result.scalars().all()]
