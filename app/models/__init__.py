# Import all models here so Alembic sees them in Base.metadata
from app.models.user import User, RefreshToken, UserRole  # noqa: F401
from app.models.ngo import NGO, NGOStatus  # noqa: F401
from app.models.program import Program, ProgramStatus  # noqa: F401
from app.models.student import Student, StudentStatus  # noqa: F401
from app.models.donor import Donor  # noqa: F401
from app.models.donation import Donation, DonationType  # noqa: F401
from app.models.invoice import Invoice, InvoiceStatus  # noqa: F401
from app.models.school import School, SchoolStatus  # noqa: F401
from app.models.application import ScholarshipApplication, ApplicationStatus  # noqa: F401
from app.models.activity_log import ActivityLog, ActivityType  # noqa: F401
from app.models.file_record import FileRecord  # noqa: F401
from app.models.allocation import Allocation  # noqa: F401

__all__ = [
    "User",
    "RefreshToken",
    "UserRole",
    "NGO",
    "NGOStatus",
    "Program",
    "ProgramStatus",
    "Student",
    "StudentStatus",
    "Donor",
    "Donation",
    "DonationType",
    "Invoice",
    "InvoiceStatus",
    "School",
    "SchoolStatus",
    "ScholarshipApplication",
    "ApplicationStatus",
    "ActivityLog",
    "ActivityType",
    "FileRecord",
    "Allocation",
]
