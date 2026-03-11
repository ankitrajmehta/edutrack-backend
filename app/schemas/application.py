from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class ApplicationCreate(BaseResponse):
    program_id: int = Field(alias="programId")
    student_name: str = Field(alias="studentName")
    age: Optional[int] = None
    grade: Optional[str] = None
    school_name: Optional[str] = Field(default=None, alias="schoolName")
    school_district: Optional[str] = Field(default=None, alias="schoolDistrict")
    guardian_name: Optional[str] = Field(default=None, alias="guardianName")
    guardian_relation: Optional[str] = Field(default=None, alias="guardianRelation")
    guardian_contact: Optional[str] = Field(default=None, alias="guardianContact")
    reason: Optional[str] = None


class ApplicationResponse(BaseResponse):
    id: int
    program_id: int = Field(alias="programId")
    student_name: str = Field(alias="studentName")
    age: Optional[int] = None
    grade: Optional[str] = None
    school_name: Optional[str] = Field(default=None, alias="schoolName")
    school_district: Optional[str] = Field(default=None, alias="schoolDistrict")
    guardian_name: Optional[str] = Field(default=None, alias="guardianName")
    guardian_relation: Optional[str] = Field(default=None, alias="guardianRelation")
    guardian_contact: Optional[str] = Field(default=None, alias="guardianContact")
    reason: Optional[str] = None
    status: str
    applied_date: datetime = Field(alias="appliedDate")
