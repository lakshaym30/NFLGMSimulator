from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Player(Base):
    """Represents a Cardinals player on the active roster, PS, or reserve lists."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(64), unique=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team_code = Column(String(8), default="ARI", nullable=False, index=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    position = Column(String(8), nullable=False)
    jersey_number = Column(Integer, nullable=True)
    status = Column(String(32), default="active", nullable=False)
    height = Column(String(16), nullable=True)
    weight = Column(Integer, nullable=True)
    birthdate = Column(Date, nullable=True)
    college = Column(String(128), nullable=True)
    experience = Column(Integer, default=0, nullable=False)
    roster_date = Column(Date, nullable=False)
    roster_source = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    team = relationship("Team", back_populates="players")
    contracts = relationship(
        "Contract", back_populates="player", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
