from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Team(Base):
    """NFL franchise metadata."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    espn_id = Column(String(16), unique=True, nullable=True)
    abbreviation = Column(String(8), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    short_display_name = Column(String(64), nullable=True)
    location = Column(String(128), nullable=True)
    nickname = Column(String(64), nullable=True)
    logo = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    players = relationship(
        "Player", back_populates="team", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="team", cascade="all, delete-orphan"
    )
