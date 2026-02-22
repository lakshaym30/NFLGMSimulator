"""Fetch current NFL rosters from ESPN's public API and save them to disk."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx

ESPN_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
ESPN_ROSTER_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/roster"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download all NFL rosters from ESPN's public API."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination JSON file. Defaults to data/nfl_rosters_YYYY-MM-DD.json (today's date).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout per request in seconds.",
    )
    return parser.parse_args()


def ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def fetch_team_list(client: httpx.Client) -> List[Dict[str, Any]]:
    resp = client.get(ESPN_TEAMS_URL)
    resp.raise_for_status()
    payload = resp.json()
    teams: List[Dict[str, Any]] = []
    for sport in payload.get("sports", []):
        for league in sport.get("leagues", []):
            for entry in league.get("teams", []):
                team = entry.get("team") or {}
                if not team.get("id"):
                    continue
                teams.append(
                    {
                        "id": team["id"],
                        "slug": team.get("slug"),
                        "abbreviation": team.get("abbreviation"),
                        "display_name": team.get("displayName"),
                        "short_display_name": team.get("shortDisplayName"),
                        "location": team.get("location"),
                        "name": team.get("name"),
                        "logo": team.get("logo"),
                        "links": team.get("links", []),
                    }
                )
    return teams


def _value_from(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def fetch_roster_for_team(client: httpx.Client, team_id: str) -> List[Dict[str, Any]]:
    resp = client.get(ESPN_ROSTER_URL.format(team_id=team_id))
    resp.raise_for_status()
    payload = resp.json()
    roster: List[Dict[str, Any]] = []

    groups: List[Dict[str, Any]] = payload.get("athletes") or payload.get("items") or []
    for group in groups:
        entries = (
            group.get("athletes")
            or group.get("items")
            or []
        )
        for athlete in entries:
            status = athlete.get("status")
            status_name = None
            status_active = None
            if isinstance(status, dict):
                status_name = _value_from(_value_from(status, "type"), "name") or status.get("type")
                status_active = status.get("active")
            elif isinstance(status, str):
                status_name = status

            position = athlete.get("position")
            college = athlete.get("college")
            experience = athlete.get("experience")

            roster.append(
                {
                    "player_id": f"espn-{athlete.get('id')}",
                    "espn_id": athlete.get("id"),
                    "first_name": athlete.get("firstName"),
                    "last_name": athlete.get("lastName"),
                    "full_name": athlete.get("fullName"),
                    "display_height": athlete.get("displayHeight"),
                    "display_weight": athlete.get("displayWeight"),
                    "height": athlete.get("height"),
                    "weight": athlete.get("weight"),
                    "age": athlete.get("age"),
                    "date_of_birth": athlete.get("birthDate"),
                    "position": _value_from(position, "abbreviation")
                    or _value_from(position, "displayName"),
                    "position_name": _value_from(position, "name") or position,
                    "jersey": athlete.get("jersey"),
                    "experience": _value_from(experience, "years") or experience,
                    "college": _value_from(college, "name") or college,
                    "status": status_name,
                    "active": status_active,
                    "headshot": _value_from(athlete.get("headshot"), "href"),
                    "links": athlete.get("links", []),
                    "contract": athlete.get("contract"),
                }
            )
    return roster


def write_payload(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    ensure_repo_root_on_path()

    timestamp = datetime.now(tz=timezone.utc)
    default_output = (
        Path("data")
        / f"nfl_rosters_{timestamp.strftime('%Y-%m-%d')}.json"
    )
    output_path = args.output or default_output

    with httpx.Client(timeout=args.timeout, headers={"User-Agent": "cardinals-gm-sim/0.1"}) as client:
        teams = fetch_team_list(client)
        rosters: List[Dict[str, Any]] = []
        for team in teams:
            roster = fetch_roster_for_team(client, team_id=team["id"])
            rosters.append(
                {
                    "team": team,
                    "roster_count": len(roster),
                    "players": roster,
                }
            )

    payload = {
        "fetched_at": timestamp.isoformat(),
        "source": {
            "name": "ESPN NFL Roster API",
            "url": ESPN_ROSTER_URL.replace("{team_id}", "<team_id>"),
            "requires_api_key": False,
        },
        "team_count": len(rosters),
        "teams": rosters,
    }

    write_payload(output_path, payload)
    print(f"Wrote {len(rosters)} team rosters to {output_path}")


if __name__ == "__main__":
    main()
