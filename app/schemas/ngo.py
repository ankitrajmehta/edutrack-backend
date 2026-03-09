from datetime import datetime
from typing import Optional, List
from pydantic import Field
from app.schemas.common import BaseResponse


class NGOCreate(BaseResponse):
    name: str
    location: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    color: Optional[str] = None


class NGOUpdate(BaseResponse):
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    color: Optional[str] = None


class NGOResponse(BaseResponse):
    id: int
    name: str
    location: str
    status: str
    description: Optional[str] = None
    tax_doc: Optional[str] = Field(default=None, alias="taxDoc")
    reg_doc: Optional[str] = Field(default=None, alias="regDoc")
    avatar: Optional[str] = None
    color: Optional[str] = None
    total_funded: float = Field(alias="totalFunded")
    students_helped: int = Field(alias="studentsHelped")
    programs_count: int = Field(alias="programsCount")
    registered_date: datetime = Field(alias="registeredDate")
