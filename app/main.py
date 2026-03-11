import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api import auth, admin, ngo, donor, school, student, public, files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EduTrack API",
    description="Transparent scholarship delivery platform",
    version="1.0.0",
)

# CORS — explicit origins only; wildcard + credentials is browser-rejected
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all global exception handlers
register_exception_handlers(app)

# Register all routers under /api prefix
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ngo.router, prefix="/api/ngo", tags=["ngo"])
app.include_router(donor.router, prefix="/api/donor", tags=["donor"])
app.include_router(school.router, prefix="/api/school", tags=["school"])
app.include_router(student.router, prefix="/api/student", tags=["student"])
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(files.router, prefix="/api/files", tags=["files"])


@app.get("/api/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint for Docker healthcheck and monitoring."""
    return {"status": "ok", "version": "1.0.0"}
