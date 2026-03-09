from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class DonorCreate(BaseResponse):
    name: str


class DonorUpdate(BaseResponse):
    name: Optional[str] = None


class DonorResponse(BaseResponse):
    id: int
    name: str
    email: str
    total_donated: float = Field(alias="totalDonated")
    donations_count: int = Field(alias="donationsCount")
