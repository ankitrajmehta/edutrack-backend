"""Schemas for NGO fund allocations."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseResponse


class AllocationCreate(BaseResponse):
    student_id: Optional[int] = Field(default=None, alias="studentId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    amount: float
    # Validation: at least one of student_id or program_id must be provided.
    # Enforced in ngo_service.create_allocation() via AppValidationError, not here.


class AllocationResponse(BaseResponse):
    id: int
    ngo_id: int = Field(alias="ngoId")
    student_id: Optional[int] = Field(default=None, alias="studentId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    amount: float
    date: datetime
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
