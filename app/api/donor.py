"""Donor API router. Read-only NGO/program/student browsing."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.schemas.ngo import NGOResponse
from app.schemas.program import ProgramResponse
from app.schemas.student import StudentResponse
from app.services import donor_service

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
