from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Transaction(Base):
    """Represents any roster/cap-altering move logged in the sim."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(32), nullable=False)
    status = Column(String(32), default="committed", nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    cap_delta = Column(Numeric(12, 2), default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    team = relationship("Team", back_populates="transactions")
