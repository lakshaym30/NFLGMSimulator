import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import Contract, ContractYear, Player, Team


@dataclass
class ImportSummary:
    teams: int
    players: int
    contracts: int


def load_payload(path: Path) -> Dict[str, Any]:
    """Load a JSON payload from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def reset_database(engine: Engine) -> None:
    """Drop and recreate tables for a clean import."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def to_decimal(value: Any) -> Decimal:
    if value in (None, "", 0):
        return Decimal("0")
    return Decimal(str(value))


def _sanitize_key(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _extract_team_entries(roster_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    teams = roster_payload.get("teams")
    if teams:
        return teams
    team_meta = roster_payload.get("team") or {}
    return [
        {
            "team": team_meta,
            "players": roster_payload.get("players", []),
        }
    ]


def _build_contract_index(
    contract_payload: Optional[Dict[str, Any]],
    team_aliases: Dict[str, str],
) -> Dict[Tuple[str, ...], Dict[str, Any]]:
    if not contract_payload:
        return {}

    contracts: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for entry in contract_payload.get("contracts", []):
        player_id = entry.get("player_id")
        if player_id:
            contracts[("id", str(player_id))] = entry
            continue

        player = _sanitize_key(entry.get("player"))
        team_field = entry.get("team")
        team_key = _sanitize_key(team_field)
        team_abbr = team_aliases.get(team_key)
        if not player or not team_abbr:
            continue
        contracts[("team", team_abbr, player)] = entry
    return contracts


def _match_contract(
    contract_lookup: Dict[Tuple[str, ...], Dict[str, Any]],
    team_abbr: str,
    external_id: str,
    first_name: str,
    last_name: str,
) -> Optional[Dict[str, Any]]:
    if not contract_lookup:
        return None

    by_id = contract_lookup.get(("id", external_id))
    if by_id:
        return by_id

    key = _sanitize_key(f"{first_name} {last_name}")
    return contract_lookup.get(("team", team_abbr, key))


def _extract_position(player_entry: Dict[str, Any]) -> str:
    position = player_entry.get("position")
    if isinstance(position, dict):
        return (
            position.get("abbreviation")
            or position.get("displayName")
            or position.get("name")
            or "UNK"
        )
    return (
        position
        or player_entry.get("position_abbr")
        or player_entry.get("position_name")
        or "UNK"
    )


def _extract_status(player_entry: Dict[str, Any]) -> str:
    status = player_entry.get("status")
    if isinstance(status, dict):
        type_field = status.get("type")
        if isinstance(type_field, dict):
            return type_field.get("name") or status.get("id") or "active"
        if isinstance(type_field, str):
            return type_field
        return status.get("name") or "active"
    if isinstance(status, str):
        return status
    return "active"


def _extract_college(player_entry: Dict[str, Any]) -> Optional[str]:
    college = player_entry.get("college")
    if isinstance(college, dict):
        return college.get("name")
    return college


def _extract_experience(player_entry: Dict[str, Any]) -> int:
    experience = player_entry.get("experience")
    if isinstance(experience, dict):
        return experience.get("years") or 0
    try:
        return int(experience or 0)
    except (TypeError, ValueError):
        return 0


def _extract_weight(player_entry: Dict[str, Any]) -> Optional[int]:
    weight = player_entry.get("weight")
    if isinstance(weight, (int, float)):
        return int(weight)
    if isinstance(weight, str):
        digits = re.sub(r"[^0-9]", "", weight)
        if digits:
            return int(digits)
    return None


def import_dataset(
    session: Session,
    roster_payload: Dict[str, Any],
    contract_payload: Optional[Dict[str, Any]] = None,
) -> ImportSummary:
    """Persist roster (league or single-team) and optional contract data into SQLite."""
    fetched_at = parse_datetime(roster_payload.get("fetched_at"))
    as_of_date = parse_date(roster_payload.get("as_of_date"))
    roster_date = as_of_date or (fetched_at.date() if fetched_at else date.today())
    roster_source_meta = roster_payload.get("source") or {}
    roster_source = roster_source_meta.get("name", "unknown")

    contract_source_meta = contract_payload.get("source") if contract_payload else {}
    contract_source_name = contract_source_meta.get("name", roster_source)
    contract_source_url = contract_source_meta.get("url")

    team_entries = _extract_team_entries(roster_payload)
    team_aliases: Dict[str, str] = {}
    team_records: List[Tuple[Dict[str, Any], Team]] = []

    teams_created = 0
    players_created = 0
    contracts_created = 0

    for entry in team_entries:
        team_meta = entry.get("team") or {}
        abbreviation = team_meta.get("abbreviation") or team_meta.get("shortDisplayName")
        if not abbreviation:
            continue

        team = Team(
            espn_id=str(team_meta.get("id")) if team_meta.get("id") else None,
            abbreviation=abbreviation.upper(),
            display_name=team_meta.get("displayName") or team_meta.get("name") or abbreviation,
            short_display_name=team_meta.get("shortDisplayName"),
            location=team_meta.get("location"),
            nickname=team_meta.get("name"),
            logo=team_meta.get("logo"),
        )
        session.add(team)
        session.flush()
        team_records.append((entry, team))
        teams_created += 1

        aliases = filter(
            None,
            {
                abbreviation,
                team.display_name,
                team.short_display_name,
                team.location,
                team.nickname,
            },
        )
        for alias in aliases:
            key = _sanitize_key(alias)
            if key:
                team_aliases[key] = team.abbreviation

    contract_lookup = _build_contract_index(contract_payload, team_aliases)

    for entry, team in team_records:
        for player_entry in entry.get("players", []):
            external_id = player_entry.get("player_id") or player_entry.get("espn_id")
            if not external_id:
                continue

            first_name = (
                (player_entry.get("first_name") or player_entry.get("firstName") or "").strip()
            )
            last_name = (
                (player_entry.get("last_name") or player_entry.get("lastName") or "").strip()
            )
            full_name = player_entry.get("full_name") or player_entry.get("fullName")
            if not first_name and full_name:
                parts = full_name.split()
                first_name = parts[0]
            if not last_name and full_name:
                parts = full_name.split()
                last_name = parts[-1] if parts else ""
            if not first_name and not last_name:
                continue

            player = Player(
                external_id=str(external_id),
                team_id=team.id,
                team_code=team.abbreviation,
                first_name=first_name,
                last_name=last_name,
                position=_extract_position(player_entry),
                jersey_number=player_entry.get("jersey_number") or player_entry.get("jersey"),
                status=_extract_status(player_entry),
                height=player_entry.get("height") or player_entry.get("display_height"),
                weight=_extract_weight(player_entry),
                birthdate=parse_date(player_entry.get("birthdate") or player_entry.get("date_of_birth")),
                college=_extract_college(player_entry),
                experience=_extract_experience(player_entry),
                roster_date=roster_date,
                roster_source=roster_source,
            )
            session.add(player)
            session.flush()
            players_created += 1

            contract_entry = _match_contract(
                contract_lookup,
                team.abbreviation,
                player.external_id,
                player.first_name,
                player.last_name,
            )
            if not contract_entry:
                continue

            contract = Contract(
                player_id=player.id,
                source=contract_source_name,
                source_url=contract_source_url,
                signed_date=parse_date(contract_entry.get("signed_date")),
                total_value=to_decimal(
                    contract_entry.get("total_value") or contract_entry.get("total")
                ),
                guaranteed=to_decimal(
                    contract_entry.get("total_guaranteed")
                    or contract_entry.get("guaranteed")
                ),
                average_per_year=to_decimal(
                    contract_entry.get("apy") or contract_entry.get("average_per_year")
                ),
                notes=contract_entry.get("notes"),
            )

            session.add(contract)
            session.flush()
            contracts_created += 1

            for year in contract_entry.get("contract_years", []) or []:
                season = year.get("season")
                if not season:
                    continue
                contract_year = ContractYear(
                    contract_id=contract.id,
                    season=int(season),
                    base_salary=to_decimal(year.get("base_salary")),
                    signing_proration=to_decimal(year.get("signing_proration")),
                    roster_bonus=to_decimal(year.get("roster_bonus")),
                    workout_bonus=to_decimal(year.get("workout_bonus")),
                    other_bonus=to_decimal(year.get("other_bonus")),
                    cap_hit=to_decimal(year.get("cap_hit")),
                    cash=to_decimal(year.get("cash")),
                    guaranteed=to_decimal(year.get("guaranteed")),
                    rolling_guarantee=to_decimal(year.get("rolling_guarantee")),
                    is_void_year=bool(year.get("is_void_year", False)),
                )
                session.add(contract_year)

    session.commit()
    return ImportSummary(teams=teams_created, players=players_created, contracts=contracts_created)
