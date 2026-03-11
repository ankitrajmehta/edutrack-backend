from datetime import datetime
from typing import Optional, List, Any
from pydantic import Field
from app.schemas.common import BaseResponse


class InvoiceCreate(BaseResponse):
    ngo_id: int = Field(alias="ngoId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    category: str
    items: List[Any] = []  # [{"desc": str, "amount": float}]


class InvoiceUpdate(BaseResponse):
    status: Optional[str] = None


class InvoiceResponse(BaseResponse):
    id: int
    school_id: int = Field(alias="schoolId")
    school_name: str = Field(alias="schoolName")
    ngo_id: int = Field(alias="ngoId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    amount: float
    category: str
    status: str
    items: List[Any] = []
    date: datetime
    approved_date: Optional[datetime] = Field(default=None, alias="approvedDate")
    supporting_doc: Optional[str] = Field(default=None, alias="supportingDoc")
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
