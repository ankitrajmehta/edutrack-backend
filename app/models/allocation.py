"""Allocation model — tracks NGO fund allocations to students or programs."""

import enum
from datetime import datetime

from sqlalchemy import Column, Float, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    ngo_id = Column(
        Integer, ForeignKey("ngos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    tx_hash = Column(String(128), nullable=True)

    # Relationships — lazy="raise_on_sql" prevents accidental N+1 cascade loading.
    ngo = relationship("NGO", lazy="raise_on_sql")
    student = relationship("Student", lazy="raise_on_sql")
    program = relationship("Program", lazy="raise_on_sql")
