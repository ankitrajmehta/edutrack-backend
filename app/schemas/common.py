from pydantic import BaseModel, ConfigDict


class BaseResponse(BaseModel):
    """Base for all ORM response schemas. Enables from_attributes and camelCase aliases."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorResponse(BaseModel):
    detail: str
    code: str
    statusCode: int


class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    """Stub for future pagination support."""

    total: int
    items: list
