import logging
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    def __init__(self, resource: str, id: Any):
        self.resource = resource
        self.id = id
        self.detail = f"{resource} {id} not found"
        self.code = "NOT_FOUND"
        self.status_code = 404


class ForbiddenError(Exception):
    def __init__(self, reason: str = "Insufficient permissions"):
        self.detail = reason
        self.code = "FORBIDDEN"
        self.status_code = 403


class ConflictError(Exception):
    def __init__(self, field: str, value: Any):
        self.detail = f"{field} '{value}' already exists"
        self.code = "CONFLICT"
        self.status_code = 409


class UnauthorizedError(Exception):
    def __init__(self, reason: str = "Invalid or expired token"):
        self.detail = reason
        self.code = "UNAUTHORIZED"
        self.status_code = 401


class AppValidationError(Exception):
    def __init__(self, message: str):
        self.detail = message
        self.code = "VALIDATION_ERROR"
        self.status_code = 422


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code,
                "statusCode": exc.status_code,
            },
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code,
                "statusCode": exc.status_code,
            },
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code,
                "statusCode": exc.status_code,
            },
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code,
                "statusCode": exc.status_code,
            },
        )

    @app.exception_handler(AppValidationError)
    async def validation_error_handler(request: Request, exc: AppValidationError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": exc.code,
                "statusCode": exc.status_code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: RequestValidationError
    ):
        detail = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        return JSONResponse(
            status_code=422,
            content={"detail": detail, "code": "VALIDATION_ERROR", "statusCode": 422},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception on %s %s", request.method, request.url, exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "code": "INTERNAL_ERROR",
                "statusCode": 500,
            },
        )
