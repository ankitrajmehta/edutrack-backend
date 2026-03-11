"""
Public schemas for unauthenticated API endpoints.

Provides: ActivityResponse, PublicNGOResponse, PublicProgramResponse.
Used by: app/api/public.py for public endpoint response serialization.
"""

from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class ActivityResponse(BaseResponse):
    """Public activity feed entry."""

    type: str
    color: str = "gray"
    text: str
    time: str  # ISO 8601 string — frontend computes relative ("2 hours ago")


class PublicNGOResponse(BaseResponse):
    """Public NGO response — verified NGOs only, no internal fields."""

    id: int
    name: str
    location: str
    status: str
    description: str
    avatar: Optional[str] = None
    color: Optional[str] = None
    total_funded: float = Field(alias="totalFunded")
    students_helped: int = Field(alias="studentsHelped")
    programs_count: int = Field(alias="programsCount")
    registered_date: str = Field(alias="registeredDate")
    # EXCLUDE: tax_doc, reg_doc (internal admin fields)
    # EXCLUDE: user_id (internal field)


class PublicProgramResponse(BaseResponse):
    """Public program response — active programs only."""

    id: int
    ngo_id: int = Field(alias="ngoId")
    name: str
    description: Optional[str] = None
    status: str
    categories: list = []
    total_budget: float = Field(alias="totalBudget")
    allocated: float
    students_enrolled: int = Field(alias="studentsEnrolled")
    start_date: Optional[str] = Field(default=None, alias="startDate")
    end_date: Optional[str] = Field(default=None, alias="endDate")
