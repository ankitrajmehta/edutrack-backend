import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProgramStatus(str, enum.Enum):
    active = "active"
    completed = "completed"


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    ngo_id = Column(
        Integer, ForeignKey("ngos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(String(2000))
    status = Column(SAEnum(ProgramStatus), default=ProgramStatus.active, nullable=False)
    categories = Column(JSON, default=list)  # ["tuition", "books", ...]
    total_budget = Column(Float, default=0.0, nullable=False)
    allocated = Column(Float, default=0.0, nullable=False)
    students_enrolled = Column(Integer, default=0, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    ngo = relationship("NGO", back_populates="programs", lazy="joined")
    students = relationship("Student", back_populates="program", lazy="selectin")
    donations = relationship("Donation", back_populates="program", lazy="selectin")
    invoices = relationship("Invoice", back_populates="program", lazy="selectin")
    applications = relationship(
        "ScholarshipApplication", back_populates="program", lazy="selectin"
    )
