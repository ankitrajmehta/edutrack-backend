"""
Admin schemas.

Provides: AdminStatsResponse, BlacklistResponse.
Used by: app/api/admin.py for response serialization.
"""

from typing import List
from pydantic import Field
from app.schemas.common import BaseResponse
from app.schemas.ngo import NGOResponse
from app.schemas.student import StudentResponse


class AdminStatsResponse(BaseResponse):
    """Platform-wide aggregated statistics for admin dashboard."""

    total_donations: float = Field(alias="totalDonations")
    total_students: int = Field(alias="totalStudents")
    total_ngos: int = Field(alias="totalNGOs")
    total_programs: int = Field(alias="totalPrograms")
    total_schools: int = Field(alias="totalSchools")
    funds_allocated: float = Field(alias="fundsAllocated")
    funds_utilized: float = Field(alias="fundsUtilized")


class BlacklistResponse(BaseResponse):
    """Combined view of blacklisted NGOs and students."""

    ngos: List[NGOResponse]
    students: List[StudentResponse]
