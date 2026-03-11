"""Donor API router. Read-only NGO/program/student browsing."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_blockchain, require_role
from app.schemas.ngo import NGOResponse
from app.schemas.program import ProgramResponse
from app.schemas.student import StudentResponse
from app.schemas.donation import (
    DonationCreate,
    DonationResponse,
    DonationDetailResponse,
)
from app.services import donor_service
from app.services.blockchain.base import BlockchainService

router = APIRouter()


@router.get("/browse/ngos", response_model=list[NGOResponse])
async def browse_ngos(
    current_user=Depends(require_role("donor")),
    db: AsyncSession = Depends(get_db),
) -> list[NGOResponse]:
    return await donor_service.browse_ngos(db)


@router.get("/browse/programs", response_model=list[ProgramResponse])
async def browse_programs(
    current_user=Depends(require_role("donor")),
    db: AsyncSession = Depends(get_db),
) -> list[ProgramResponse]:
    return await donor_service.browse_programs(db)


@router.get("/browse/students", response_model=list[StudentResponse])
async def browse_students(
    current_user=Depends(require_role("donor")),
    db: AsyncSession = Depends(get_db),
) -> list[StudentResponse]:
    return await donor_service.browse_students(db)


@router.post("/donations", response_model=DonationResponse, status_code=201)
async def create_donation(
    data: DonationCreate,
    current_user=Depends(require_role("donor")),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
) -> DonationResponse:
    return await donor_service.create_donation(db, data, current_user, blockchain)


@router.get("/donations", response_model=list[DonationResponse])
async def list_donations(
    current_user=Depends(require_role("donor")),
    db: AsyncSession = Depends(get_db),
) -> list[DonationResponse]:
    return await donor_service.list_donations(db, current_user)


@router.get("/donations/{donation_id}", response_model=DonationDetailResponse)
async def get_donation_detail(
    donation_id: int,
    current_user=Depends(require_role("donor")),
    db: AsyncSession = Depends(get_db),
) -> DonationDetailResponse:
    return await donor_service.get_donation_detail(db, donation_id, current_user)
