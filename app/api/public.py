"""
Public API endpoints — no authentication required.

Provides: /stats, /activity, /ngos, /programs
Router is registered under /api/public prefix in main.py.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.admin import AdminStatsResponse
from app.schemas.public import (
    ActivityResponse,
    PublicNGOResponse,
    PublicProgramResponse,
)
from app.services import admin_service, public_service

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
async def public_stats(db: AsyncSession = Depends(get_db)):
    """
    Public platform statistics — no authentication required.
    Returns aggregated stats matching mock.js platformStats shape.
    """
    return await admin_service.get_stats(db)


@router.get("/activity", response_model=List[ActivityResponse])
async def public_activity(db: AsyncSession = Depends(get_db)):
    """
    Public activity feed — all ActivityLog entries, newest first.
    Each entry has {type, color, text, time} where time is ISO 8601 string.
    """
    return await public_service.get_activity(db)


@router.get("/ngos", response_model=List[PublicNGOResponse])
async def public_ngos(db: AsyncSession = Depends(get_db)):
    """
    Verified NGOs — public fields only, no auth required.
    Returns only NGOs with status='verified'.
    """
    return await public_service.get_public_ngos(db)


@router.get("/programs", response_model=List[PublicProgramResponse])
async def public_programs(db: AsyncSession = Depends(get_db)):
    """
    Active programs — public fields only, no auth required.
    Returns only programs with status='active'.
    """
    return await public_service.get_public_programs(db)
