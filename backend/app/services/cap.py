"""Utility helpers for salary cap calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.core.config import settings
from app.models import Contract, ContractYear


@dataclass
class CapImpact:
    cap_hit: float
    savings: float
    dead_money_current: float
    dead_money_future: float = 0.0


def _to_float(value: Optional[Decimal]) -> float:
    if value is None:
        return 0.0
    return float(value)


def _target_year(year: Optional[int]) -> int:
    return year or settings.cap_year


def _pick_year(contract: Optional[Contract], *, year: Optional[int] = None) -> Optional[ContractYear]:
    if not contract or not contract.years:
        return None
    desired_year = _target_year(year)
    ordered = sorted(contract.years, key=lambda yr: yr.season)
    exact = next((yr for yr in ordered if yr.season == desired_year), None)
    if exact:
        return exact
    future = next((yr for yr in ordered if yr.season > desired_year), None)
    return future or ordered[-1]


def cap_hit_from_contract(contract: Optional[Contract], *, year: Optional[int] = None) -> float:
    if not contract:
        return 0.0
    year_entry = _pick_year(contract, year=year)
    if year_entry:
        base = _to_float(year_entry.base_salary)
        signing = _to_float(year_entry.signing_proration)
        roster = _to_float(year_entry.roster_bonus)
        workout = _to_float(year_entry.workout_bonus)
        other = _to_float(year_entry.other_bonus)
        computed = base + signing + roster + workout + other
        cap_hit = _to_float(year_entry.cap_hit) or computed
        return round(cap_hit, 2)
    if contract.average_per_year:
        return round(_to_float(contract.average_per_year), 2)
    if contract.total_value:
        return round(_to_float(contract.total_value), 2)
    return 0.0


def guaranteed_from_contract(contract: Optional[Contract], *, year: Optional[int] = None) -> float:
    if not contract:
        return 0.0
    year_entry = _pick_year(contract, year=year)
    if year_entry:
        rolling = _to_float(year_entry.rolling_guarantee)
        if rolling > 0:
            return rolling
        guaranteed = _to_float(year_entry.guaranteed)
        if guaranteed > 0:
            return guaranteed
    return _to_float(contract.guaranteed)


def release_cap_impact(contract: Optional[Contract], *, post_june_1: bool = False, year: Optional[int] = None) -> CapImpact:
    """Approximate savings/dead money for a release or trade."""
    target_year = _target_year(year)
    cap_hit = cap_hit_from_contract(contract, year=target_year)
    guaranteed = guaranteed_from_contract(contract, year=target_year)

    if cap_hit <= 0:
        return CapImpact(cap_hit=0.0, savings=0.0, dead_money_current=0.0)

    baseline_dead = cap_hit * 0.4
    dead_money = guaranteed if guaranteed > 0 else baseline_dead
    dead_money = min(cap_hit, dead_money)
    savings = max(cap_hit - dead_money, 0.0)

    if post_june_1 and dead_money > 0:
        current = round(dead_money / 2, 2)
        future = round(dead_money - current, 2)
    else:
        current = round(dead_money, 2)
        future = 0.0

    return CapImpact(
        cap_hit=round(cap_hit, 2),
        savings=round(savings, 2),
        dead_money_current=current,
        dead_money_future=future,
    )
