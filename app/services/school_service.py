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
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.school import SchoolResponse
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services import activity_service


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


async def create_invoice(
    db: AsyncSession, data: InvoiceCreate, current_user: User
) -> InvoiceResponse:
    """SCHL-03: Submit invoice — status=pending, no blockchain call, amount computed from items."""
    result = await db.execute(select(School).where(School.user_id == current_user.id))
    school = result.scalar_one_or_none()
    if school is None:
        raise NotFoundError("School profile", current_user.id)

    # Amount is sum of line items — no client-supplied top-level amount field
    amount = sum(
        item["amount"] if isinstance(item, dict) else item.amount for item in data.items
    )

    # Serialize items to plain dicts for JSON column storage
    items_data = [
        item if isinstance(item, dict) else item.model_dump() for item in data.items
    ]

    invoice = Invoice(
        school_id=school.id,
        ngo_id=data.ngo_id,
        program_id=data.program_id,
        school_name=school.name,
        amount=amount,
        category=data.category,
        status=InvoiceStatus.pending,
        items=items_data,
    )
    db.add(invoice)

    school.total_invoiced = school.total_invoiced + amount

    await activity_service.log(
        db,
        "invoice",
        f"{school.name} submitted invoice for {data.category} (${amount:,.2f})",
        current_user.id,
    )
    await db.commit()
    await db.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


async def list_invoices(db: AsyncSession, current_user: User) -> list[InvoiceResponse]:
    """SCHL-04: List authenticated school's invoices only (ownership-scoped by school_id)."""
    result = await db.execute(select(School).where(School.user_id == current_user.id))
    school = result.scalar_one_or_none()
    if school is None:
        raise NotFoundError("School profile", current_user.id)

    result = await db.execute(
        select(Invoice)
        .where(Invoice.school_id == school.id)
        .order_by(Invoice.id.desc())
    )
    return [InvoiceResponse.model_validate(i) for i in result.scalars().all()]
