from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Contract(Base):
    """Top-level contract metadata for a player."""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(128), nullable=False)
    source_url = Column(String(256), nullable=True)
    signed_date = Column(Date, nullable=True)
    total_value = Column(Numeric(12, 2), nullable=True)
    guaranteed = Column(Numeric(12, 2), nullable=True)
    average_per_year = Column(Numeric(12, 2), nullable=True)
    notes = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    player = relationship("Player", back_populates="contracts")
    years = relationship(
        "ContractYear", back_populates="contract", cascade="all, delete-orphan"
    )


class ContractYear(Base):
    """Per-season breakdown for a contract."""

    __tablename__ = "contract_years"

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    season = Column(Integer, nullable=False)
    base_salary = Column(Numeric(12, 2), default=0, nullable=False)
    signing_proration = Column(Numeric(12, 2), default=0, nullable=False)
    roster_bonus = Column(Numeric(12, 2), default=0, nullable=False)
    workout_bonus = Column(Numeric(12, 2), default=0, nullable=False)
    other_bonus = Column(Numeric(12, 2), default=0, nullable=False)
    cap_hit = Column(Numeric(12, 2), default=0, nullable=False)
    cash = Column(Numeric(12, 2), default=0, nullable=False)
    guaranteed = Column(Numeric(12, 2), default=0, nullable=False)
    rolling_guarantee = Column(Numeric(12, 2), default=0, nullable=False)
    is_void_year = Column(Boolean, default=False, nullable=False)

    contract = relationship("Contract", back_populates="years")
