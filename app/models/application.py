import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class ScholarshipApplication(Base):
    __tablename__ = "scholarship_applications"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_name = Column(String(255), nullable=False)
    age = Column(Integer)
    grade = Column(String(50))
    school_name = Column(String(255))
    school_district = Column(String(255))
    guardian_name = Column(String(255))
    guardian_relation = Column(String(100))
    guardian_contact = Column(String(100))
    reason = Column(Text)
    status = Column(
        SAEnum(ApplicationStatus), default=ApplicationStatus.pending, nullable=False
    )
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    submitted_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships — lazy="raise_on_sql" prevents accidental N+1 cascade loading.
    program = relationship(
        "Program", back_populates="applications", lazy="raise_on_sql"
    )
