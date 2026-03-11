from pydantic import Field
from app.schemas.common import BaseResponse


class FileUploadResponse(BaseResponse):
    """Response schema for file upload — returns file ID and retrieval URL."""

    file_id: int = Field(alias="fileId")
    url: str
