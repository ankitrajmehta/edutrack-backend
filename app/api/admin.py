"""
Admin API router.

All endpoints require role="admin". Route handlers are thin: one service call, return result.
Service layer owns all db.commit() calls — never commit in route handlers.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.schemas.admin import AdminStatsResponse, BlacklistResponse
from app.schemas.ngo import NGOResponse
from app.schemas.student import StudentResponse
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminStatsResponse)
async def get_dashboard(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:
    return await admin_service.get_stats(db)


@router.get("/ngos", response_model=list[NGOResponse])
async def list_ngos(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: pending/verified/rejected/blacklisted",
    ),
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[NGOResponse]:
    return await admin_service.list_ngos(db, status=status)


@router.patch("/ngos/{ngo_id}/verify", response_model=NGOResponse)
async def verify_ngo(
    ngo_id: int,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> NGOResponse:
    return await admin_service.update_ngo_status(db, ngo_id, "verify", current_user.id)


@router.patch("/ngos/{ngo_id}/reject", response_model=NGOResponse)
async def reject_ngo(
    ngo_id: int,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> NGOResponse:
    return await admin_service.update_ngo_status(db, ngo_id, "reject", current_user.id)


@router.patch("/ngos/{ngo_id}/blacklist", response_model=NGOResponse)
async def blacklist_ngo(
    ngo_id: int,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> NGOResponse:
    return await admin_service.update_ngo_status(
        db, ngo_id, "blacklist", current_user.id
    )


@router.patch("/ngos/{ngo_id}/restore", response_model=NGOResponse)
async def restore_ngo(
    ngo_id: int,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> NGOResponse:
    return await admin_service.update_ngo_status(db, ngo_id, "restore", current_user.id)


@router.get("/blacklist", response_model=BlacklistResponse)
async def get_blacklist(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> BlacklistResponse:
    return await admin_service.get_blacklist(db)


@router.patch("/students/{student_id}/blacklist", response_model=StudentResponse)
async def blacklist_student(
    student_id: int,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    return await admin_service.update_student_status(
        db, student_id, "blacklist", current_user.id
    )


@router.patch("/students/{student_id}/restore", response_model=StudentResponse)
async def restore_student(
    student_id: int,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    return await admin_service.update_student_status(
        db, student_id, "restore", current_user.id
    )
