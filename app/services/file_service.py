"""
File service.

upload_file: async disk write via aiofiles + FileRecord DB insert.
download_file: FastAPIFileResponse streaming — no manual aiofiles read needed.

CRITICAL: All disk I/O uses aiofiles.open() — never blocking open() in async context (FILE-03).
"""

import os
import uuid

import aiofiles
from fastapi import UploadFile
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.file_record import FileRecord
from app.models.user import User
from app.schemas.file import FileUploadResponse


# Role → upload subdirectory mapping (S3-compatible prefix structure)
_FOLDER_MAP: dict[str, str] = {
    "ngo": "ngo",
    "school": "school",
}


async def upload_file(
    db: AsyncSession, file: UploadFile, current_user: User
) -> FileUploadResponse:
    """
    Write uploaded file to disk asynchronously and persist a FileRecord.

    Storage path: uploads/{role}/{uuid4}{ext}
    Returns: FileUploadResponse with file_id (DB primary key) and retrieval URL.
    """
    # Determine upload subdirectory by role (unknown roles go to misc/)
    folder = _FOLDER_MAP.get(current_user.role.value, "misc")
    upload_dir = os.path.join("uploads", folder)
    os.makedirs(
        upload_dir, exist_ok=True
    )  # sync mkdir is fine — no I/O wait, just syscall

    # Generate unique filename preserving original extension
    original_name = file.filename or "upload"
    ext = os.path.splitext(original_name)[1]  # e.g. ".pdf", ".png", ""
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(upload_dir, stored_name)

    # Read file content once (UploadFile.read() is async)
    content = await file.read()

    # Async write — CRITICAL: never use blocking open() in async context
    async with aiofiles.open(stored_path, "wb") as f:
        await f.write(content)

    # Persist FileRecord to DB
    record = FileRecord(
        original_name=original_name,
        stored_path=stored_path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        uploaded_by=current_user.id,
    )
    db.add(record)
    await db.commit()

    return FileUploadResponse(file_id=record.id, url=f"/api/files/{record.id}")


async def download_file(db: AsyncSession, file_id: int) -> FastAPIFileResponse:
    """
    Return the file at the stored path.

    FastAPIFileResponse handles async streaming internally — no manual aiofiles read needed.
    If the file does not exist in DB, raises NotFoundError (HTTP 404).
    """
    record = await db.get(FileRecord, file_id)
    if record is None:
        raise NotFoundError("File", file_id)

    # FastAPIFileResponse streams the file; FastAPI handles Content-Disposition header
    return FastAPIFileResponse(
        path=record.stored_path,
        filename=record.original_name,
        media_type=record.mime_type,
    )
