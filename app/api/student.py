"""Student API router. Browse programs, submit and view own applications."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.schemas.program import ProgramResponse
from app.schemas.application import ApplicationCreate, ApplicationResponse
from app.services import student_service

router = APIRouter()


@router.get("/programs", response_model=list[ProgramResponse])
async def browse_programs(
    current_user=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
) -> list[ProgramResponse]:
    return await student_service.browse_programs(db)


@router.post("/apply", response_model=ApplicationResponse, status_code=201)
async def submit_application(
    data: ApplicationCreate,
    current_user=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    return await student_service.submit_application(db, data, current_user)


@router.get("/applications", response_model=list[ApplicationResponse])
async def list_own_applications(
    current_user=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationResponse]:
    return await student_service.list_own_applications(db, current_user)
