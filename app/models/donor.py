from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class Donor(Base):
    __tablename__ = "donors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    total_donated = Column(Float, default=0.0, nullable=False)
    donations_count = Column(Integer, default=0, nullable=False)

    # Relationships — lazy="raise_on_sql" prevents accidental N+1 cascade loading.
    user = relationship("User", lazy="raise_on_sql")
    donations = relationship("Donation", back_populates="donor", lazy="raise_on_sql")
