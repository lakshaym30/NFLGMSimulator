"""Simple scouting board + draft simulator."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Team

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "prospects.json"


class DraftError(Exception):
    pass


@lru_cache(maxsize=1)
def load_prospect_board() -> Dict[str, any]:
    if not DATA_PATH.exists():
        raise DraftError(f"Prospect board missing at {DATA_PATH}. Populate it before running the draft simulator.")
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def list_prospects() -> List[Dict[str, any]]:
    board = load_prospect_board()
    return board.get("prospects", [])


def simulate_draft(session: Session, team_code: str, rounds: int = 7) -> Dict[str, any]:
    if rounds < 1:
        raise DraftError("Rounds must be >= 1")
    board = sorted(list_prospects(), key=lambda p: p.get("grade", 0), reverse=True)
    if not board:
        raise DraftError("Prospect board empty")

    teams = session.scalars(select(Team).order_by(Team.abbreviation)).all()
    if not teams:
        raise DraftError("No teams in database")
    team_codes = [team.abbreviation for team in teams]
    if team_code.upper() not in team_codes:
        raise DraftError(f"Unknown team {team_code}")

    picks: List[Dict[str, any]] = []
    board_index = 0
    total_picks = min(len(board), len(team_codes) * rounds)
    for pick_number in range(total_picks):
        team_slot = team_codes[pick_number % len(team_codes)]
        if board_index >= len(board):
            break
        prospect = board[board_index]
        board_index += 1
        picks.append(
            {
                "overall": pick_number + 1,
                "round": (pick_number // len(team_codes)) + 1,
                "team": team_slot,
                "prospect": prospect,
            }
        )

    team_picks = [pick for pick in picks if pick["team"] == team_code.upper()]
    return {
        "team": team_code.upper(),
        "rounds": rounds,
        "picks": picks,
        "team_picks": team_picks,
        "prospects_remaining": board[board_index:],
    }
