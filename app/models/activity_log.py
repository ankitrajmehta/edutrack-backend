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


class ActivityType(str, enum.Enum):
    donation = "donation"
    invoice = "invoice"
    verify = "verify"
    allocation = "allocation"
    program = "program"
    blacklist = "blacklist"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SAEnum(ActivityType), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    actor = relationship("User", back_populates="activity_logs", lazy="joined")
