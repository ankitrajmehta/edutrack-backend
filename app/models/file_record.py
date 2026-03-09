from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.core.database import Base


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    mime_type = Column(String(100))
    size_bytes = Column(BigInteger)
    uploaded_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    uploader = relationship("User", back_populates="file_records", lazy="joined")
