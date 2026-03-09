import enum
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


class SchoolStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    status = Column(SAEnum(SchoolStatus), default=SchoolStatus.pending, nullable=False)
    students_in_programs = Column(Integer, default=0, nullable=False)
    total_invoiced = Column(Float, default=0.0, nullable=False)

    user = relationship("User", lazy="joined")
    invoices = relationship("Invoice", back_populates="school", lazy="selectin")
