"""
NGO API router.

get_current_ngo: local dependency that resolves the authenticated NGO profile.
All handlers receive a typed NGO object (not raw user_id) for ownership scoping.
"""

from fastapi import APIRouter, Depends, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.core.dependencies import get_db, require_role, get_blockchain
from app.core.exceptions import NotFoundError
from app.models.ngo import NGO
from app.schemas.ngo import NGOStatsResponse, ApplicationRejectRequest
from app.schemas.program import ProgramCreate, ProgramUpdate, ProgramResponse
from app.schemas.student import StudentCreate, StudentResponse
from app.schemas.application import ApplicationResponse
from app.schemas.invoice import InvoiceResponse
from app.schemas.allocation import AllocationCreate, AllocationResponse
from app.services import ngo_service
from app.services.blockchain.base import BlockchainService

router = APIRouter(tags=["ngo"])


async def get_current_ngo(
    current_user=Depends(require_role("ngo")),
    db: AsyncSession = Depends(get_db),
) -> NGO:
    """Resolve the authenticated user's NGO profile. Raises 404 if no NGO profile exists."""
    result = await db.execute(select(NGO).where(NGO.user_id == current_user.id))
    ngo = result.scalar_one_or_none()
    if ngo is None:
        raise NotFoundError("NGO profile", current_user.id)
    return ngo


@router.get("/dashboard", response_model=NGOStatsResponse)
async def get_dashboard(
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> NGOStatsResponse:
    return await ngo_service.get_dashboard(db, ngo)


@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    data: ProgramCreate,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("ngo")),
) -> ProgramResponse:
    return await ngo_service.create_program(db, data, ngo, current_user.id)


@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> list[ProgramResponse]:
    return await ngo_service.list_programs(db, ngo)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: int,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    return await ngo_service.get_program(db, program_id, ngo)


@router.put("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: int,
    data: ProgramUpdate,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("ngo")),
) -> ProgramResponse:
    return await ngo_service.update_program(db, program_id, data, ngo, current_user.id)


@router.delete("/programs/{program_id}", status_code=204)
async def delete_program(
    program_id: int,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("ngo")),
) -> None:
    await ngo_service.delete_program(db, program_id, ngo, current_user.id)


@router.post("/students", response_model=StudentResponse, status_code=201)
async def register_student(
    data: StudentCreate,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
    current_user=Depends(require_role("ngo")),
) -> StudentResponse:
    return await ngo_service.register_student(
        db, data, ngo, blockchain, current_user.id
    )


@router.get("/students", response_model=list[StudentResponse])
async def list_students(
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> list[StudentResponse]:
    return await ngo_service.list_students(db, ngo)


@router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    return await ngo_service.get_student(db, student_id, ngo)


@router.get("/applications", response_model=list[ApplicationResponse])
async def list_applications(
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationResponse]:
    return await ngo_service.list_applications(db, ngo)


@router.patch(
    "/applications/{application_id}/accept",
    response_model=StudentResponse,
    status_code=201,
)
async def accept_application(
    application_id: int,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
    current_user=Depends(require_role("ngo")),
) -> StudentResponse:
    return await ngo_service.accept_application(
        db, application_id, ngo, blockchain, current_user.id
    )


@router.patch(
    "/applications/{application_id}/reject", response_model=ApplicationResponse
)
async def reject_application(
    application_id: int,
    data: ApplicationRejectRequest,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("ngo")),
) -> ApplicationResponse:
    return await ngo_service.reject_application(
        db, application_id, ngo, data.reason, current_user.id
    )


# ─── Invoice & Allocation endpoints (NGO-08 through NGO-11) ───────────────────────


class InvoiceRejectRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceResponse]:
    return await ngo_service.list_invoices(db, ngo)


@router.patch("/invoices/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(
    invoice_id: int,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
    current_user=Depends(require_role("ngo")),
) -> InvoiceResponse:
    return await ngo_service.approve_invoice(
        db, invoice_id, ngo, blockchain, current_user.id
    )


@router.patch("/invoices/{invoice_id}/reject", response_model=InvoiceResponse)
async def reject_invoice(
    invoice_id: int,
    body: InvoiceRejectRequest = Body(default_factory=InvoiceRejectRequest),
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("ngo")),
) -> InvoiceResponse:
    return await ngo_service.reject_invoice(
        db, invoice_id, ngo, current_user.id, body.reason
    )


@router.post("/allocations", response_model=AllocationResponse, status_code=201)
async def create_allocation(
    data: AllocationCreate,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
    current_user=Depends(require_role("ngo")),
) -> AllocationResponse:
    return await ngo_service.create_allocation(
        db, data, ngo, blockchain, current_user.id
    )


@router.get("/allocations", response_model=list[AllocationResponse])
async def list_allocations(
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
) -> list[AllocationResponse]:
    return await ngo_service.list_allocations(db, ngo)
