"""Generate a team-specific roster JSON from the league-wide ESPN payload."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Slice the ESPN league roster dump into a single-team roster file."
    )
    parser.add_argument(
        "--league-file",
        required=True,
        type=Path,
        help="Path to the JSON file produced by fetch_nfl_rosters.py",
    )
    parser.add_argument(
        "--team",
        required=True,
        help="Team abbreviation or numeric ESPN team ID (e.g., ARI or 22).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination JSON file for the single-team roster.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_int(value: Any) -> Optional[int]:
    try:
        if value in ("", None):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def select_team_roster(league_payload: Dict[str, Any], selector: str) -> Dict[str, Any]:
    for team_entry in league_payload.get("teams", []):
        team_info = team_entry.get("team") or team_entry.get("team_info") or team_entry
        if not team_info:
            continue
        team_id = str(team_info.get("id", "")).lower()
        abbr = (team_info.get("abbreviation") or "").lower()
        if selector.lower() in {team_id, abbr}:
            return team_entry
    raise ValueError(f"Team '{selector}' not present in league file")


def transform_roster(team_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    roster: List[Dict[str, Any]] = []
    team_meta = team_payload.get("team") or {}
    for player in team_payload.get("players", []):
        roster.append(
            {
                "player_id": player.get("player_id") or f"espn-{player.get('espn_id')}",
                "team_code": team_meta.get("abbreviation"),
                "first_name": player.get("first_name"),
                "last_name": player.get("last_name"),
                "position": player.get("position"),
                "jersey_number": safe_int(player.get("jersey")),
                "status": player.get("status") or "active",
                "height": player.get("display_height") or player.get("height"),
                "weight": safe_int(player.get("weight"))
                or safe_int(str(player.get("display_weight", "")).split(" ")[0]),
                "birthdate": player.get("date_of_birth"),
                "college": player.get("college"),
                "experience": safe_int(player.get("experience")) or 0,
            }
        )
    return roster


def main() -> None:
    args = parse_args()
    payload = load_json(args.league_file)

    team_entry = select_team_roster(payload, args.team)
    team_meta = team_entry.get("team") or team_entry.get("team_info") or {}
    roster_players = transform_roster(team_entry)

    fetched_at = payload.get("fetched_at")
    as_of_date = (
        fetched_at and datetime.fromisoformat(fetched_at.replace("Z", "+00:00")).date()
    )

    output_payload = {
        "as_of_date": str(as_of_date) if as_of_date else fetched_at,
        "source": payload.get("source"),
        "team": {
            "id": team_meta.get("id"),
            "name": team_meta.get("displayName") or team_meta.get("name"),
            "abbreviation": team_meta.get("abbreviation"),
        },
        "players": roster_players,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output_payload, handle, indent=2)
        handle.write("\n")

    print(
        f"Wrote {len(roster_players)} players for {team_meta.get('abbreviation')} to {args.output}"
    )


if __name__ == "__main__":
    main()
