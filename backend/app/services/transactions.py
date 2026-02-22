"""Business logic for transaction previews and commits."""

from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import Contract, ContractYear, Player, Team, Transaction
from app.services import cap as cap_service

# Statuses that should not be counted toward the active roster.
EXCLUDED_ROSTER_STATUSES = ("released", "retired")


class TransactionError(Exception):
    pass


def _active_players_stmt(team_id: int):
    return (
        select(Player)
        .where(Player.team_id == team_id, func.lower(Player.status).notin_(EXCLUDED_ROSTER_STATUSES))
        .options(selectinload(Player.contracts).selectinload(Contract.years))
        .order_by(Player.last_name, Player.first_name)
    )


def _team_by_code(session: Session, code: str) -> Team:
    team = session.scalar(select(Team).where(func.lower(Team.abbreviation) == code.lower()))
    if not team:
        raise TransactionError(f"Team '{code.upper()}' not found")
    return team


def _cap_totals(session: Session, team: Team) -> Tuple[float, float, float, List[Player]]:
    players = session.scalars(_active_players_stmt(team.id)).all()
    total_cap = 0.0
    for player in players:
        contract = player.contracts[0] if player.contracts else None
        total_cap += cap_service.cap_hit_from_contract(contract)
    cap_limit = float(settings.salary_cap_limit)
    cap_space = round(cap_limit - total_cap, 2)
    return cap_limit, round(total_cap, 2), cap_space, players


def _roster_limit() -> int:
    # TODO: make dynamic per league calendar.
    return 90


def _split_name(full_name: str) -> Tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "Player", "Unknown"
    if len(parts) == 1:
        return parts[0], "Unknown"
    return parts[0], " ".join(parts[1:])


def _player_snapshot(player: Player) -> Dict[str, Any]:
    return {
        "external_id": player.external_id,
        "team_id": player.team_id,
        "team_code": player.team_code,
        "first_name": player.first_name,
        "last_name": player.last_name,
        "position": player.position,
        "jersey_number": player.jersey_number,
        "status": player.status,
        "height": player.height,
        "weight": player.weight,
        "birthdate": player.birthdate.isoformat() if player.birthdate else None,
        "college": player.college,
        "experience": player.experience,
        "roster_date": player.roster_date.isoformat() if player.roster_date else None,
        "roster_source": player.roster_source,
    }


def _contract_snapshot(contract: Optional[Contract]) -> Optional[Dict[str, Any]]:
    if not contract:
        return None
    years = []
    for year in contract.years:
        years.append(
            {
                "season": year.season,
                "base_salary": float(year.base_salary or 0),
                "signing_proration": float(year.signing_proration or 0),
                "cap_hit": float(year.cap_hit or 0),
                "roster_bonus": float(year.roster_bonus or 0),
                "workout_bonus": float(year.workout_bonus or 0),
                "other_bonus": float(year.other_bonus or 0),
                "cash": float(year.cash or 0),
                "guaranteed": float(year.guaranteed or 0),
                "rolling_guarantee": float(year.rolling_guarantee or 0),
                "is_void_year": bool(year.is_void_year),
            }
        )
    return {
        "source": contract.source,
        "source_url": contract.source_url,
        "signed_date": contract.signed_date.isoformat() if contract.signed_date else None,
        "total_value": float(contract.total_value or 0),
        "average_per_year": float(contract.average_per_year or 0),
        "guaranteed": float(contract.guaranteed or 0),
        "notes": contract.notes,
        "years": years,
    }


def preview_release(session: Session, team_code: str, player_id: int, *, post_june_1: bool) -> Dict:
    team = _team_by_code(session, team_code)
    cap_limit, total_cap, cap_space, players = _cap_totals(session, team)
    player = next((p for p in players if p.id == player_id), None)
    if not player:
        raise TransactionError("Player not found on the specified team")
    contract = player.contracts[0] if player.contracts else None
    impact = cap_service.release_cap_impact(contract, post_june_1=post_june_1)
    cap_space_after = round(cap_space + impact.savings, 2)
    roster_count_after = len(players) - 1
    allowed = impact.savings > 0
    notes = [
        f"Releasing {player.full_name} saves ${impact.savings:,.0f} against the cap.",
        f"Dead money this year: ${impact.dead_money_current:,.0f}",
    ]
    if impact.dead_money_future:
        notes.append(f"Dead money next year: ${impact.dead_money_future:,.0f}")
    if cap_space_after < 0:
        notes.append("Team would remain over the cap after this move.")
    return {
        "team": team.abbreviation,
        "type": "release",
        "allowed": allowed,
        "cap_limit": cap_limit,
        "total_cap": total_cap,
        "cap_space_before": cap_space,
        "cap_space_after": cap_space_after,
        "cap_delta": round(impact.savings, 2),
        "dead_money": impact.dead_money_current,
        "dead_money_future": impact.dead_money_future,
        "roster_delta": -1,
        "roster_count_after": roster_count_after,
        "notes": notes,
        "payload": {"player_id": player_id, "post_june_1": post_june_1},
    }


def commit_release(session: Session, preview: Dict) -> Transaction:
    team = _team_by_code(session, preview["team"])
    player_id = preview["payload"]["player_id"]
    player = session.scalar(
        select(Player)
        .where(Player.id == player_id)
        .options(selectinload(Player.contracts).selectinload(Contract.years))
    )
    if not player or player.team_id != team.id:
        raise TransactionError("Player no longer on original team.")
    contract = player.contracts[0] if player.contracts else None
    snapshot = {
        "player": _player_snapshot(player),
        "contract": _contract_snapshot(contract),
    }
    session.delete(player)
    preview_with_snapshot = dict(preview)
    preview_with_snapshot["undo"] = snapshot
    record = Transaction(
        team_id=team.id,
        type="release",
        payload=preview["payload"],
        result=preview_with_snapshot,
        cap_delta=_to_decimal(preview["cap_delta"]),
        notes="; ".join(preview.get("notes", [])),
        executed_at=datetime.utcnow(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def preview_sign(
    session: Session,
    team_code: str,
    full_name: str,
    position: str,
    apy: float,
    guaranteed: float,
    years: int,
    *,
    signing_bonus: float = 0.0,
    roster_bonus: float = 0.0,
    workout_bonus: float = 0.0,
) -> Dict:
    team = _team_by_code(session, team_code)
    cap_limit, total_cap, cap_space, players = _cap_totals(session, team)
    roster_limit = _roster_limit()
    cap_delta = round(-apy, 2)
    cap_space_after = round(cap_space + cap_delta, 2)
    roster_count_after = len(players) + 1
    allowed = cap_space_after >= 0 and roster_count_after <= roster_limit
    notes = [
        f"Signing {full_name} adds ${apy:,.0f} to the current cap.",
        f"Guaranteed cash: ${guaranteed:,.0f}",
    ]
    if signing_bonus:
        notes.append(f"Signing bonus of ${signing_bonus:,.0f} prorates over {min(years, 5)} years.")
    if roster_count_after > roster_limit:
        notes.append(f"Roster limit ({roster_limit}) exceeded.")
    if cap_space_after < 0:
        notes.append("Team would be over the cap.")
    payload = {
        "full_name": full_name,
        "position": position,
        "apy": apy,
        "guaranteed": guaranteed,
        "years": years,
        "signing_bonus": signing_bonus,
        "roster_bonus": roster_bonus,
        "workout_bonus": workout_bonus,
    }
    return {
        "team": team.abbreviation,
        "type": "sign",
        "allowed": allowed,
        "cap_limit": cap_limit,
        "total_cap": total_cap,
        "cap_space_before": cap_space,
        "cap_space_after": cap_space_after,
        "cap_delta": cap_delta,
        "dead_money": 0.0,
        "dead_money_future": 0.0,
        "roster_delta": 1,
        "roster_count_after": roster_count_after,
        "notes": notes,
        "payload": payload,
    }


def commit_sign(session: Session, preview: Dict) -> Transaction:
    team = _team_by_code(session, preview["team"])
    payload = preview["payload"]
    first_name, last_name = _split_name(payload["full_name"])
    today = date.today()
    apy = _to_decimal(payload["apy"])
    guaranteed = _to_decimal(payload.get("guaranteed", 0))
    years = max(int(payload.get("years", 1)), 1)
    signing_bonus = _to_decimal(payload.get("signing_bonus", 0))
    roster_bonus = _to_decimal(payload.get("roster_bonus", 0))
    workout_bonus = _to_decimal(payload.get("workout_bonus", 0))
    player = Player(
        external_id=f"fa-{today.strftime('%Y%m%d')}-{int(datetime.utcnow().timestamp())}",
        team_id=team.id,
        team_code=team.abbreviation,
        first_name=first_name,
        last_name=last_name,
        position=payload["position"],
        status="active",
        experience=0,
        roster_date=today,
        roster_source="Manual Entry",
    )
    session.add(player)
    session.flush()

    contract = Contract(
        player_id=player.id,
        source="Manual Entry",
        total_value=apy * years,
        average_per_year=apy,
        guaranteed=guaranteed,
    )
    session.add(contract)
    session.flush()

    proration_years = min(years, 5)
    signing_proration = (
        signing_bonus / proration_years if proration_years and signing_bonus > 0 else Decimal("0")
    )
    remaining_guarantee = guaranteed
    for year_index in range(years):
        roster_bonus_year = roster_bonus if year_index == 0 else Decimal("0")
        workout_bonus_year = workout_bonus if year_index == 0 else Decimal("0")
        base_salary = apy - signing_proration - roster_bonus_year - workout_bonus_year
        if base_salary < 0:
            base_salary = Decimal("0")
        cap_hit = base_salary + signing_proration + roster_bonus_year + workout_bonus_year
        cash = base_salary + roster_bonus_year + workout_bonus_year
        if year_index == 0:
            cash += signing_bonus
        guarantee_for_year = min(remaining_guarantee, cash)
        rolling = remaining_guarantee
        remaining_guarantee = max(Decimal("0"), remaining_guarantee - guarantee_for_year)
        session.add(
            ContractYear(
                contract_id=contract.id,
                season=settings.cap_year + year_index,
                base_salary=base_salary,
                signing_proration=signing_proration,
                roster_bonus=roster_bonus_year,
                workout_bonus=workout_bonus_year,
                other_bonus=Decimal("0"),
                cap_hit=cap_hit,
                cash=cash,
                guaranteed=guarantee_for_year,
                rolling_guarantee=rolling,
                is_void_year=False,
            )
        )

    record = Transaction(
        team_id=team.id,
        type="sign",
        payload=payload,
        result=preview,
        cap_delta=_to_decimal(preview["cap_delta"]),
        notes="; ".join(preview.get("notes", [])),
        executed_at=datetime.utcnow(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def preview_trade(
    session: Session,
    team_code: str,
    send_player_ids: List[int],
    receive_player_ids: List[int],
    partner_team_code: str,
    post_june_1: bool = False,
) -> Dict:
    team = _team_by_code(session, team_code)
    partner = _team_by_code(session, partner_team_code)
    cap_limit, total_cap, cap_space, players = _cap_totals(session, team)
    partner_cap_limit, partner_total_cap, partner_cap_space, partner_players = _cap_totals(
        session, partner
    )
    send_players = [p for p in players if p.id in send_player_ids]
    receive_players = [p for p in partner_players if p.id in receive_player_ids]
    if len(send_players) != len(send_player_ids):
        raise TransactionError("One or more outgoing players not found on team")
    if len(receive_players) != len(receive_player_ids):
        raise TransactionError("One or more incoming players not found on partner team")

    outgoing_savings = sum(
        cap_service.release_cap_impact(p.contracts[0] if p.contracts else None, post_june_1=post_june_1).savings
        for p in send_players
    )
    incoming_cap = sum(
        cap_service.cap_hit_from_contract(p.contracts[0] if p.contracts else None)
        for p in receive_players
    )
    cap_delta = round(outgoing_savings - incoming_cap, 2)
    cap_space_after = round(cap_space + cap_delta, 2)
    roster_delta = len(receive_players) - len(send_players)
    roster_count_after = len(players) + roster_delta

    partner_outgoing_savings = sum(
        cap_service.release_cap_impact(p.contracts[0] if p.contracts else None, post_june_1=post_june_1).savings
        for p in receive_players
    )
    partner_incoming_cap = sum(
        cap_service.cap_hit_from_contract(p.contracts[0] if p.contracts else None)
        for p in send_players
    )
    partner_cap_delta = round(partner_outgoing_savings - partner_incoming_cap, 2)
    partner_cap_space_after = round(partner_cap_space + partner_cap_delta, 2)
    partner_roster_delta = -roster_delta
    partner_roster_after = len(partner_players) + partner_roster_delta

    roster_limit = _roster_limit()
    requires_cap_space = cap_delta < 0
    partner_requires_cap_space = partner_cap_delta < 0
    allowed = True
    if roster_count_after > roster_limit or partner_roster_after > roster_limit:
        allowed = False
    if requires_cap_space and cap_space_after < 0:
        allowed = False
    if partner_requires_cap_space and partner_cap_space_after < 0:
        allowed = False

    notes = [
        f"Outgoing savings: ${outgoing_savings:,.0f}",
        f"Incoming cap hits: ${incoming_cap:,.0f}",
    ]
    if not allowed:
        notes.append("Either team would violate cap or roster constraints.")

    payload = {
        "send_player_ids": send_player_ids,
        "receive_player_ids": receive_player_ids,
        "partner_team_code": partner_team_code,
        "post_june_1": post_june_1,
    }

    return {
        "team": team.abbreviation,
        "type": "trade",
        "allowed": allowed,
        "cap_limit": cap_limit,
        "total_cap": total_cap,
        "cap_space_before": cap_space,
        "cap_space_after": cap_space_after,
        "cap_delta": cap_delta,
        "dead_money": 0.0,
        "dead_money_future": 0.0,
        "roster_delta": roster_delta,
        "roster_count_after": roster_count_after,
        "notes": notes,
        "payload": payload,
        "partner": {
            "team": partner.abbreviation,
            "cap_space_before": partner_cap_space,
            "cap_space_after": partner_cap_space_after,
            "cap_delta": partner_cap_delta,
            "roster_delta": partner_roster_delta,
            "roster_count_after": partner_roster_after,
        },
    }


def commit_trade(session: Session, preview: Dict) -> Transaction:
    team = _team_by_code(session, preview["team"])
    partner = _team_by_code(session, preview["partner"]["team"])
    payload = preview["payload"]
    send_ids = payload["send_player_ids"]
    receive_ids = payload["receive_player_ids"]

    send_players = session.scalars(
        select(Player)
        .where(Player.id.in_(send_ids))
        .options(selectinload(Player.contracts).selectinload(Contract.years))
    ).all()
    receive_players = session.scalars(
        select(Player)
        .where(Player.id.in_(receive_ids))
        .options(selectinload(Player.contracts).selectinload(Contract.years))
    ).all()

    for player in send_players:
        if player.team_id != team.id:
            raise TransactionError(f"{player.full_name} no longer on {team.abbreviation}")
        player.team_id = partner.id
        player.team_code = partner.abbreviation
    for player in receive_players:
        if player.team_id != partner.id:
            raise TransactionError(f"{player.full_name} no longer on {partner.abbreviation}")
        player.team_id = team.id
        player.team_code = team.abbreviation

    record = Transaction(
        team_id=team.id,
        type="trade",
        payload=payload,
        result=preview,
        cap_delta=_to_decimal(preview["cap_delta"]),
        notes="; ".join(preview.get("notes", [])),
        executed_at=datetime.utcnow(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def undo_transaction(session: Session, transaction_id: int) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise TransactionError("Transaction not found")
    if transaction.status == "undone":
        raise TransactionError("Transaction already undone")
    if transaction.type != "release":
        raise TransactionError("Undo supported only for releases right now")

    undo_payload = (transaction.result or {}).get("undo")
    if not undo_payload:
        raise TransactionError("Transaction missing undo snapshot")

    player_snapshot = undo_payload.get("player")
    if not player_snapshot:
        raise TransactionError("Player snapshot unavailable")

    player = Player(
        external_id=player_snapshot.get("external_id"),
        team_id=player_snapshot.get("team_id"),
        team_code=player_snapshot.get("team_code"),
        first_name=player_snapshot.get("first_name"),
        last_name=player_snapshot.get("last_name"),
        position=player_snapshot.get("position"),
        jersey_number=player_snapshot.get("jersey_number"),
        status=player_snapshot.get("status", "active"),
        height=player_snapshot.get("height"),
        weight=player_snapshot.get("weight"),
        birthdate=_parse_iso_date(player_snapshot.get("birthdate")),
        college=player_snapshot.get("college"),
        experience=int(player_snapshot.get("experience", 0)),
        roster_date=_parse_iso_date(player_snapshot.get("roster_date")) or date.today(),
        roster_source=player_snapshot.get("roster_source", "Undo Restore"),
    )
    session.add(player)
    session.flush()

    contract_snapshot = undo_payload.get("contract")
    if contract_snapshot:
        contract = Contract(
            player_id=player.id,
            source=contract_snapshot.get("source", "Undo Restore"),
            source_url=contract_snapshot.get("source_url"),
            signed_date=_parse_iso_date(contract_snapshot.get("signed_date")),
            total_value=_to_decimal(contract_snapshot.get("total_value")),
            average_per_year=_to_decimal(contract_snapshot.get("average_per_year")),
            guaranteed=_to_decimal(contract_snapshot.get("guaranteed")),
            notes=contract_snapshot.get("notes"),
        )
        session.add(contract)
        session.flush()

        for year in contract_snapshot.get("years", []):
            season = year.get("season")
            if not season:
                continue
            session.add(
                ContractYear(
                    contract_id=contract.id,
                    season=int(season),
                    base_salary=_to_decimal(year.get("base_salary")),
                    signing_proration=_to_decimal(year.get("signing_proration")),
                    roster_bonus=_to_decimal(year.get("roster_bonus")),
                    workout_bonus=_to_decimal(year.get("workout_bonus")),
                    other_bonus=_to_decimal(year.get("other_bonus")),
                    cap_hit=_to_decimal(year.get("cap_hit")),
                    cash=_to_decimal(year.get("cash")),
                    guaranteed=_to_decimal(year.get("guaranteed")),
                    rolling_guarantee=_to_decimal(year.get("rolling_guarantee")),
                    is_void_year=bool(year.get("is_void_year")),
                )
            )

    transaction.status = "undone"
    session.commit()
    session.refresh(transaction)
    return transaction


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
def _to_decimal(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))
