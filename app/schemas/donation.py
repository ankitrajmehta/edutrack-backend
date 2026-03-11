from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class DonationCreate(BaseResponse):
    ngo_id: int = Field(alias="ngoId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    student_id: Optional[int] = Field(default=None, alias="studentId")
    amount: float
    type: str = Field(pattern="^(general|program|student)$")
    message: Optional[str] = None


class DonationResponse(BaseResponse):
    id: int
    donor_id: int = Field(alias="donorId")
    ngo_id: int = Field(alias="ngoId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    student_id: Optional[int] = Field(default=None, alias="studentId")
    amount: float
    date: datetime
    type: str
    message: Optional[str] = None
    tx_hash: Optional[str] = Field(default=None, alias="txHash")


class FundFlowAllocation(BaseResponse):
    """Allocation summary embedded in donation fund-flow detail."""

    id: int
    student_id: Optional[int] = Field(default=None, alias="studentId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    amount: float
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
    date: datetime


class FundFlowInvoice(BaseResponse):
    """Invoice summary embedded in donation fund-flow detail."""

    id: int
    school_name: str = Field(alias="schoolName")
    amount: float
    status: str
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
    approved_date: Optional[datetime] = Field(default=None, alias="approvedDate")


class DonationDetailResponse(DonationResponse):
    """Donation with complete fund-flow chain: donation → allocations → invoice settlements."""

    allocations: list[FundFlowAllocation] = []
    invoices: list[FundFlowInvoice] = []
