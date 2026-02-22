"""Market intelligence, free agency, and trade negotiation helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import Contract, Player, Team
from app.services import cap as cap_service
from app.services import transactions as transaction_service
from app.services.transactions import TransactionError

FREE_AGENT_PATH = Path(__file__).resolve().parents[3] / "data" / "free_agents.json"
POSITION_TARGETS: Dict[str, int] = {
    "QB": 3,
    "RB": 5,
    "WR": 9,
    "TE": 4,
    "OT": 4,
    "G": 4,
    "C": 2,
    "DL": 6,
    "EDGE": 6,
    "LB": 6,
    "CB": 8,
    "S": 5,
    "K": 1,
    "P": 1,
    "LS": 1,
    "DEFAULT": 4,
}


class MarketError(Exception):
    """Raised when the market service cannot fulfill a request."""


@lru_cache(maxsize=1)
def load_free_agent_board() -> Dict[str, Any]:
    if not FREE_AGENT_PATH.exists():
        return {"free_agents": []}
    with FREE_AGENT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _team_by_code(session: Session, code: str) -> Team:
    team = session.scalar(select(Team).where(func.lower(Team.abbreviation) == code.lower()))
    if not team:
        raise MarketError(f"Team '{code.upper()}' not found")
    return team


def _team_snapshot(session: Session, team: Team) -> Tuple[List[Player], float, float]:
    players = session.scalars(
        select(Player)
        .where(Player.team_id == team.id)
        .options(selectinload(Player.contracts).selectinload(Contract.years))
    ).all()
    total_cap = sum(cap_service.cap_hit_from_contract(p.contracts[0] if p.contracts else None) for p in players)
    cap_limit = float(settings.salary_cap_limit)
    cap_space = round(cap_limit - total_cap, 2)
    return players, total_cap, cap_space


def _position_counts(players: List[Player]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for player in players:
        counts[player.position] = counts.get(player.position, 0) + 1
    return counts


def _desired_depth(position: str) -> int:
    return POSITION_TARGETS.get(position.upper(), POSITION_TARGETS["DEFAULT"])


def _fit_score(position_counts: Dict[str, int], position: str) -> int:
    desired = _desired_depth(position)
    have = position_counts.get(position, 0)
    need = max(desired - have, 0)
    ratio = need / desired if desired else 0
    return int(min(96, 40 + ratio * 60))


def _contender_score(cap_space: float, total_cap: float) -> int:
    cap_limit = float(settings.salary_cap_limit)
    spend_ratio = min(total_cap / cap_limit if cap_limit else 0.0, 1.2)
    score = int(max(30, min(95, spend_ratio * 90)))
    if cap_space < 0:
        score = max(25, score - 10)
    return score


def _value_score(market_value: float, pool_values: List[float]) -> float:
    filtered = [value for value in pool_values if value]
    if not filtered or not market_value:
        return 1.0
    med = median(filtered)
    if med <= 0:
        return 1.0
    return round(min(1.5, max(0.5, market_value / med)), 2)


def list_free_agents(session: Session, team_code: str) -> List[Dict[str, Any]]:
    team = _team_by_code(session, team_code)
    players, total_cap, cap_space = _team_snapshot(session, team)
    counts = _position_counts(players)
    board = load_free_agent_board().get("free_agents", [])
    pool_values = [agent.get("market_value", 0) or 0 for agent in board]
    contender = _contender_score(cap_space, total_cap)

    entries: List[Dict[str, Any]] = []
    for profile in board:
        position = profile.get("position", "ATH")
        fit = _fit_score(counts, position)
        notes = []
        desired = _desired_depth(position)
        notes.append(f"{team.abbreviation} carries {counts.get(position, 0)}/{desired} ideal {position} bodies.")
        notes.append(f"Cap space available: ${cap_space:,.0f}.")
        entries.append(
            {
                "id": profile.get("id"),
                "name": profile.get("name"),
                "position": position,
                "age": profile.get("age"),
                "market_value": profile.get("market_value"),
                "traits": profile.get("traits", []),
                "preferred_roles": profile.get("preferred_roles", []),
                "last_team": profile.get("last_team"),
                "preferred_years": profile.get("preferred_years", []),
                "scheme_fits": profile.get("scheme_fits", []),
                "fit_score": fit,
                "contender_score": contender,
                "value_score": _value_score(profile.get("market_value", 0) or 0, pool_values),
                "notes": notes,
            }
        )
    return entries


def list_trade_targets(session: Session, team_code: str, limit: int = 20) -> List[Dict[str, Any]]:
    target_team = _team_by_code(session, team_code)
    target_players, target_cap, target_cap_space = _team_snapshot(session, target_team)
    target_counts = _position_counts(target_players)

    entries: List[Dict[str, Any]] = []
    all_teams = session.scalars(select(Team).order_by(Team.abbreviation)).all()
    for team in all_teams:
        if team.id == target_team.id:
            continue
        roster, total_cap, cap_space = _team_snapshot(session, team)
        partner_counts = _position_counts(roster)
        contender = _contender_score(cap_space, total_cap)
        for player in roster:
            contract = player.contracts[0] if player.contracts else None
            cap_hit = cap_service.cap_hit_from_contract(contract)
            if cap_hit <= 0:
                continue
            fit_score = _fit_score(target_counts, player.position)
            desired = _desired_depth(player.position)
            depth = partner_counts.get(player.position, 0)
            surplus = max(depth - desired, 0)
            availability_score = int(min(95, 35 + surplus * 8 + (max(-cap_space, 0) / 2_000_000)))
            years_remaining = 0
            if contract and contract.years:
                years_remaining = max(
                    0,
                    max(year.season for year in contract.years) - settings.cap_year + 1,
                )
            notes = [
                f"{team.abbreviation} depth at {player.position}: {depth}/{desired}.",
                f"Cap space after move could reach ${cap_space + cap_hit:,.0f}.",
            ]
            entries.append(
                {
                    "player_id": player.id,
                    "name": player.full_name,
                    "position": player.position,
                    "team": {
                        "code": team.abbreviation,
                        "display_name": team.display_name,
                        "logo": team.logo,
                    },
                    "cap_hit": round(cap_hit, 2),
                    "years_remaining": years_remaining,
                    "fit_score": fit_score,
                    "availability_score": availability_score,
                    "contender_score": contender,
                    "notes": notes,
                }
            )
    entries.sort(key=lambda item: (item["fit_score"] + item["availability_score"]), reverse=True)
    return entries[:limit]


def evaluate_free_agent_offer(
    session: Session,
    *,
    team_code: str,
    free_agent_id: str,
    apy: float,
    years: int,
    signing_bonus: float,
    roster_bonus: float,
    workout_bonus: float,
) -> Dict[str, Any]:
    board = {agent["id"]: agent for agent in load_free_agent_board().get("free_agents", [])}
    profile = board.get(free_agent_id)
    if not profile:
        raise MarketError("Unknown free-agent profile.")
    team = _team_by_code(session, team_code)
    roster, total_cap, cap_space = _team_snapshot(session, team)
    counts = _position_counts(roster)
    fit_score = _fit_score(counts, profile.get("position", "ATH"))
    contender = _contender_score(cap_space, total_cap)
    market_value = profile.get("market_value") or apy
    value_ratio = apy / market_value if market_value else 1.0
    desired_years = profile.get("preferred_years") or [3, 4]
    within_years = desired_years[0] <= years <= desired_years[-1]

    interest = 0.5 * min(1.5, value_ratio) + 0.3 * (fit_score / 100) + 0.2 * (contender / 100)
    if not within_years:
        interest -= 0.1

    guaranteed = signing_bonus + roster_bonus + workout_bonus
    preview = transaction_service.preview_sign(
        session,
        team_code,
        profile["name"],
        profile.get("position", "ATH"),
        apy,
        guaranteed or apy * 0.4,
        years,
        signing_bonus=signing_bonus,
        roster_bonus=roster_bonus,
        workout_bonus=workout_bonus,
    )
    notes = preview.get("notes", []).copy()

    accepted = interest >= 0.95 and preview["allowed"]
    if not accepted:
        counter = {
            "apy": round(max(market_value * 0.97, market_value), -4),
            "years": desired_years[-1],
            "signing_bonus": max(signing_bonus, market_value * 0.3),
        }
        if not preview["allowed"]:
            notes.append("Cap or roster limits block this contract.")
        return {
            "accepted": False,
            "type": "free_agent",
            "notes": notes,
            "counter": counter,
            "cap_space_after": preview["cap_space_after"],
        }

    transaction = transaction_service.commit_sign(session, preview)
    notes.append(f"{profile['name']} accepted a {years}-year offer averaging ${apy:,.0f}.")
    return {
        "accepted": True,
        "type": "free_agent",
        "notes": notes,
        "cap_space_after": preview["cap_space_after"],
        "transaction_id": transaction.id,
    }


def evaluate_trade_offer(
    session: Session,
    *,
    team_code: str,
    partner_team_code: str,
    send_player_ids: List[int],
    receive_player_ids: List[int],
    post_june_1: bool,
) -> Dict[str, Any]:
    preview = transaction_service.preview_trade(
        session,
        team_code,
        send_player_ids,
        receive_player_ids,
        partner_team_code,
        post_june_1=post_june_1,
    )
    outgoing_value = abs(preview["cap_delta"])
    partner_delta = preview["partner"]["cap_delta"]
    fairness = 1.0
    if outgoing_value and partner_delta:
        fairness = min(2.0, max(0.2, abs(partner_delta) / outgoing_value))
    if not preview["allowed"] or fairness < 0.6 or fairness > 1.4:
        notes = preview.get("notes", []).copy()
        if fairness < 0.6:
            notes.append("Partner rejected: offer too lopsided.")
        if fairness > 1.4:
            notes.append("Your outgoing value exceeds the return; sweetener recommended.")
        return {
            "accepted": False,
            "type": "trade",
            "notes": notes,
            "cap_space_after": preview["cap_space_after"],
            "counter": {
                "request": "Adjust player mix or add draft compensation to balance the deal."
            },
        }
    transaction = transaction_service.commit_trade(session, preview)
    notes = preview.get("notes", []).copy()
    notes.append("Trade executed after AI approval.")
    return {
        "accepted": True,
        "type": "trade",
        "notes": notes,
        "cap_space_after": preview["cap_space_after"],
        "transaction_id": transaction.id,
    }
