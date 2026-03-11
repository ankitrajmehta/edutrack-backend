import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class StudentStatus(str, enum.Enum):
    active = "active"
    graduated = "graduated"
    blacklisted = "blacklisted"


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index("ix_students_scholarship_id", "scholarship_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    ngo_id = Column(
        Integer, ForeignKey("ngos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    age = Column(Integer)
    school = Column(String(255))
    grade = Column(String(50))
    guardian = Column(String(255))
    location = Column(String(255))
    scholarship_id = Column(String(20), unique=True)  # EDU-YYYY-XXXXX
    wallet_address = Column(String(100))  # Mock blockchain wallet address
    wallet_balance = Column(Float, default=0.0, nullable=False)
    total_received = Column(Float, default=0.0, nullable=False)
    status = Column(SAEnum(StudentStatus), default=StudentStatus.active, nullable=False)

    # Relationships — lazy="raise_on_sql" prevents accidental N+1 cascade loading.
    ngo = relationship("NGO", back_populates="students", lazy="raise_on_sql")
    program = relationship("Program", back_populates="students", lazy="raise_on_sql")
    donations = relationship("Donation", back_populates="student", lazy="raise_on_sql")
