from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.common import BaseResponse, MessageResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(ngo|donor|school|student)$")
    name: str = Field(min_length=1, max_length=255)
    # Optional role-specific fields for profile creation
    location: Optional[str] = None
    description: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(default="bearer", alias="tokenType")

    model_config = {"populate_by_name": True}


class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class LogoutRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class UserResponse(BaseResponse):
    id: int
    email: str
    role: str
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")


class NGOProfileResponse(BaseResponse):
    """Merged user + NGO profile — shape matches mock.js NGO object."""

    id: int
    email: str
    role: str
    name: str
    location: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    color: Optional[str] = None
    total_funded: float = Field(default=0.0, alias="totalFunded")
    students_helped: int = Field(default=0, alias="studentsHelped")
    programs_count: int = Field(default=0, alias="programsCount")
    registered_date: Optional[datetime] = Field(default=None, alias="registeredDate")
    created_at: datetime = Field(alias="createdAt")


class DonorProfileResponse(BaseResponse):
    """Merged user + donor profile."""

    id: int
    email: str
    role: str
    name: str
    total_donated: float = Field(default=0.0, alias="totalDonated")
    donations_count: int = Field(default=0, alias="donationsCount")
    created_at: datetime = Field(alias="createdAt")


class SchoolProfileResponse(BaseResponse):
    """Merged user + school profile."""

    id: int
    email: str
    role: str
    name: str
    location: Optional[str] = None
    status: Optional[str] = None
    students_in_programs: int = Field(default=0, alias="studentsInPrograms")
    total_invoiced: float = Field(default=0.0, alias="totalInvoiced")
    created_at: datetime = Field(alias="createdAt")


class StudentProfileResponse(BaseResponse):
    """Merged user + student profile."""

    id: int
    email: str
    role: str
    name: str
    age: Optional[int] = None
    school: Optional[str] = None
    grade: Optional[str] = None
    guardian: Optional[str] = None
    location: Optional[str] = None
    scholarship_id: Optional[str] = Field(default=None, alias="scholarshipId")
    wallet_balance: float = Field(default=0.0, alias="walletBalance")
    total_received: float = Field(default=0.0, alias="totalReceived")
    status: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")


class AdminProfileResponse(BaseResponse):
    """Admin has no separate profile model — just user fields."""

    id: int
    email: str
    role: str
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")


# Union type for GET /me response
ProfileResponse = (
    NGOProfileResponse
    | DonorProfileResponse
    | SchoolProfileResponse
    | StudentProfileResponse
    | AdminProfileResponse
)
