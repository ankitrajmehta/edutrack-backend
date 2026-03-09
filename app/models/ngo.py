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
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class NGOStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    blacklisted = "blacklisted"


class NGO(Base):
    __tablename__ = "ngos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    status = Column(SAEnum(NGOStatus), default=NGOStatus.pending, nullable=False)
    description = Column(String(2000))
    tax_doc = Column(String(500))  # file path or URL
    reg_doc = Column(String(500))  # file path or URL
    avatar = Column(String(500))
    color = Column(String(50))
    total_funded = Column(Float, default=0.0, nullable=False)
    students_helped = Column(Integer, default=0, nullable=False)
    programs_count = Column(Integer, default=0, nullable=False)
    registered_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", lazy="joined")
    programs = relationship("Program", back_populates="ngo", lazy="selectin")
    students = relationship("Student", back_populates="ngo", lazy="selectin")
