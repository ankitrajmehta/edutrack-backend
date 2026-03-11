from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class StudentCreate(BaseResponse):
    name: str
    age: Optional[int] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    guardian: Optional[str] = None
    location: Optional[str] = None
    program_id: int = Field(alias="programId")


class StudentUpdate(BaseResponse):
    name: Optional[str] = None
    age: Optional[int] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    guardian: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None


class StudentResponse(BaseResponse):
    id: int
    name: str
    age: Optional[int] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    guardian: Optional[str] = None
    program_id: Optional[int] = Field(default=None, alias="programId")
    ngo_id: Optional[int] = Field(default=None, alias="ngoId")
    scholarship_id: Optional[str] = Field(default=None, alias="scholarshipId")
    wallet_address: Optional[str] = Field(default=None, alias="walletAddress")
    wallet_balance: float = Field(alias="walletBalance")
    total_received: float = Field(alias="totalReceived")
    status: str
    location: Optional[str] = None
