import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Float,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Enum as SAEnum,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class DonationType(str, enum.Enum):
    general = "general"
    program = "program"
    student = "student"


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(
        Integer, ForeignKey("donors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ngo_id = Column(
        Integer, ForeignKey("ngos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    type = Column(SAEnum(DonationType), nullable=False)
    message = Column(Text)
    tx_hash = Column(String(128))

    donor = relationship("Donor", back_populates="donations", lazy="joined")
    ngo = relationship("NGO", lazy="joined")
    program = relationship("Program", back_populates="donations", lazy="joined")
    student = relationship("Student", back_populates="donations", lazy="joined")
