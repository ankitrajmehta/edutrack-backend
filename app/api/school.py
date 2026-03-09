"""School API router. Profile registration and retrieval."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.schemas.school import SchoolResponse
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services import school_service

router = APIRouter()


@router.post("/register", response_model=SchoolResponse, status_code=201)
async def register(
    current_user=Depends(require_role("school")),
    db: AsyncSession = Depends(get_db),
) -> SchoolResponse:
    return await school_service.register(db, current_user)


@router.get("/profile", response_model=SchoolResponse)
async def get_profile(
    current_user=Depends(require_role("school")),
    db: AsyncSession = Depends(get_db),
) -> SchoolResponse:
    return await school_service.get_profile(db, current_user)


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    current_user=Depends(require_role("school")),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    return await school_service.create_invoice(db, data, current_user)


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    current_user=Depends(require_role("school")),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceResponse]:
    return await school_service.list_invoices(db, current_user)
