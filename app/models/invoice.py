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
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    school_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    status = Column(
        SAEnum(InvoiceStatus), default=InvoiceStatus.pending, nullable=False
    )
    items = Column(JSON, default=list)  # [{"desc": str, "amount": float}]
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_date = Column(DateTime, nullable=True)
    supporting_doc = Column(String(500))
    tx_hash = Column(String(128), nullable=True)

    # Relationships — lazy="raise_on_sql" prevents accidental N+1 cascade loading.
    school = relationship("School", back_populates="invoices", lazy="raise_on_sql")
    ngo = relationship("NGO", lazy="raise_on_sql")
    program = relationship("Program", back_populates="invoices", lazy="raise_on_sql")
