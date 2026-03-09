from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class SchoolCreate(BaseResponse):
    name: str
    location: Optional[str] = None


class SchoolUpdate(BaseResponse):
    name: Optional[str] = None
    location: Optional[str] = None


class SchoolResponse(BaseResponse):
    id: int
    name: str
    location: Optional[str] = None
    status: str
    students_in_programs: int = Field(alias="studentsInPrograms")
    total_invoiced: float = Field(alias="totalInvoiced")
