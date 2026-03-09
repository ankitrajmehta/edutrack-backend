"""
Donor service.

Read-only browsing of verified NGOs, active programs, and active students.
No ownership scoping — donors browse public-facing verified/active records.
No activity logging — read operations don't write activity entries.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.ngo import NGO, NGOStatus
from app.models.program import Program, ProgramStatus
from app.models.student import Student, StudentStatus
from app.models.allocation import Allocation
from app.models.donation import Donation, DonationType
from app.models.donor import Donor
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.ngo import NGOResponse
from app.schemas.program import ProgramResponse
from app.schemas.student import StudentResponse
from app.schemas.donation import (
    DonationCreate,
    DonationResponse,
    DonationDetailResponse,
)
from app.schemas.donation import FundFlowAllocation, FundFlowInvoice
from app.services import activity_service
from app.services.blockchain.base import BlockchainService


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


async def create_donation(
    db: AsyncSession,
    data: DonationCreate,
    current_user,
    blockchain: BlockchainService,
) -> DonationResponse:
    """DONOR-04: Create donation, call blockchain.donate(), record txHash."""
    result = await db.execute(select(Donor).where(Donor.user_id == current_user.id))
    donor = result.scalar_one_or_none()
    if donor is None:
        raise NotFoundError("Donor profile", current_user.id)

    # Determine target for blockchain call
    if data.student_id:
        target_type = "student"
        target_id = str(data.student_id)
    elif data.program_id:
        target_type = "program"
        target_id = str(data.program_id)
    else:
        target_type = "ngo"
        target_id = str(data.ngo_id)

    # Blockchain FIRST — tx_hash must exist before commit
    tx = await blockchain.donate(str(donor.id), target_type, target_id, data.amount)

    donation = Donation(
        donor_id=donor.id,
        ngo_id=data.ngo_id,
        program_id=data.program_id,
        student_id=data.student_id,
        amount=data.amount,
        type=DonationType(data.type),
        message=data.message,
        tx_hash=tx.tx_hash,
    )
    db.add(donation)

    donor.total_donated = donor.total_donated + data.amount
    donor.donations_count = donor.donations_count + 1

    target_name = (
        f"NGO #{data.ngo_id}"
        if not data.program_id and not data.student_id
        else f"program/student #{target_id}"
    )
    await activity_service.log(
        db,
        "donation",
        f"{donor.name} donated ${data.amount:,.2f} to {target_name}",
        current_user.id,
    )
    await db.commit()
    await db.refresh(donation)
    return DonationResponse.model_validate(donation)


async def list_donations(db: AsyncSession, current_user) -> list[DonationResponse]:
    """DONOR-05: List authenticated donor's donations only (ownership-scoped)."""
    result = await db.execute(select(Donor).where(Donor.user_id == current_user.id))
    donor = result.scalar_one_or_none()
    if donor is None:
        raise NotFoundError("Donor profile", current_user.id)

    result = await db.execute(
        select(Donation)
        .where(Donation.donor_id == donor.id)
        .order_by(Donation.id.desc())
    )
    donations = result.scalars().all()
    return [DonationResponse.model_validate(d) for d in donations]


async def get_donation_detail(
    db: AsyncSession, donation_id: int, current_user
) -> DonationDetailResponse:
    """DONOR-06: Get donation with fund-flow chain (allocations + invoices)."""
    result = await db.execute(
        select(Donation)
        .where(Donation.id == donation_id)
        .options(joinedload(Donation.donor))
    )
    donation = result.scalar_one_or_none()
    if donation is None:
        raise NotFoundError("Donation", donation_id)

    # Ownership check — only the donor who made this donation can view the detail
    if donation.donor.user_id != current_user.id:
        raise ForbiddenError("You can only view your own donations")

    # Build fund-flow chain
    allocations: list[FundFlowAllocation] = []
    invoices: list[FundFlowInvoice] = []

    if donation.program_id:
        alloc_result = await db.execute(
            select(Allocation).where(Allocation.program_id == donation.program_id)
        )
        allocations = [
            FundFlowAllocation.model_validate(a) for a in alloc_result.scalars().all()
        ]
        inv_result = await db.execute(
            select(Invoice).where(
                Invoice.program_id == donation.program_id,
                Invoice.status == InvoiceStatus.approved,
            )
        )
        invoices = [
            FundFlowInvoice.model_validate(i) for i in inv_result.scalars().all()
        ]
    elif donation.student_id:
        alloc_result = await db.execute(
            select(Allocation).where(Allocation.student_id == donation.student_id)
        )
        allocations = [
            FundFlowAllocation.model_validate(a) for a in alloc_result.scalars().all()
        ]

    detail = DonationDetailResponse.model_validate(donation)
    detail.allocations = allocations
    detail.invoices = invoices
    return detail
