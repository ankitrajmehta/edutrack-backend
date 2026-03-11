"""
Files API router.

POST /upload — any authenticated user can upload (no role restriction).
GET /{id}   — any authenticated user can download by file ID.

Both endpoints require a valid Bearer token (get_current_user enforces authentication).
No role restriction at the file service level — file access is by ID possession.
"""

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.schemas.file import FileUploadResponse
from app.services import file_service

router = APIRouter(tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileUploadResponse:
    """Upload a file. Returns {fileId, url}. Any authenticated user can upload."""
    return await file_service.upload_file(db, file, current_user)


@router.get("/{file_id}", response_class=FastAPIFileResponse)
async def download_file(
    file_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download file by ID. Returns file bytes with original filename. Any authenticated user."""
    return await file_service.download_file(db, file_id)
