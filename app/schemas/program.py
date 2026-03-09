from datetime import datetime
from typing import Optional, List
from pydantic import Field
from app.schemas.common import BaseResponse


class ProgramCreate(BaseResponse):
    name: str
    description: Optional[str] = None
    categories: List[str] = []
    total_budget: float = Field(alias="totalBudget")
    start_date: Optional[datetime] = Field(default=None, alias="startDate")
    end_date: Optional[datetime] = Field(default=None, alias="endDate")


class ProgramUpdate(BaseResponse):
    name: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    total_budget: Optional[float] = Field(default=None, alias="totalBudget")
    status: Optional[str] = None
    start_date: Optional[datetime] = Field(default=None, alias="startDate")
    end_date: Optional[datetime] = Field(default=None, alias="endDate")


class ProgramResponse(BaseResponse):
    id: int
    ngo_id: int = Field(alias="ngoId")
    name: str
    description: Optional[str] = None
    status: str
    categories: List[str] = []
    total_budget: float = Field(alias="totalBudget")
    allocated: float
    students_enrolled: int = Field(alias="studentsEnrolled")
    start_date: Optional[datetime] = Field(default=None, alias="startDate")
    end_date: Optional[datetime] = Field(default=None, alias="endDate")
