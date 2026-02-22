"""Simple season simulator (schedule + standings)."""

from __future__ import annotations

import random
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Team


class SeasonSimError(Exception):
    pass


DIVISIONS: Dict[str, List[str]] = {
    "AFC East": ["BUF", "MIA", "NE", "NYJ"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West": ["DEN", "KC", "LAC", "LV"],
    "NFC East": ["DAL", "NYG", "PHI", "WAS"],
    "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"],
    "NFC West": ["ARI", "SEA", "SF", "LAR"],
}


def simulate_season(session: Session, team_code: str, weeks: int = 17) -> Dict[str, any]:
    teams = session.scalars(select(Team).order_by(Team.abbreviation)).all()
    if not teams:
        raise SeasonSimError("No teams available to simulate")
    team_codes = [team.abbreviation for team in teams]
    if team_code.upper() not in team_codes:
        raise SeasonSimError(f"Unknown team {team_code}")

    rng = random.Random(team_code)
    opponents = [code for code in team_codes if code != team_code.upper()]
    if not opponents:
        raise SeasonSimError("Need at least two teams")

    games: List[Dict[str, any]] = []
    wins = 0
    losses = 0
    ties = 0
    for week in range(weeks):
        opponent = opponents[week % len(opponents)]
        home = week % 2 == 0
        team_score = rng.randint(13, 35)
        opp_score = rng.randint(10, 33)
        if team_score == opp_score:
            team_score += 1
        if team_score > opp_score:
            result = "W"
            wins += 1
        elif team_score < opp_score:
            result = "L"
            losses += 1
        else:
            result = "T"
            ties += 1
        games.append(
            {
                "week": week + 1,
                "home": home,
                "opponent": opponent,
                "team_score": team_score,
                "opponent_score": opp_score,
                "result": result,
            }
        )

    standings = {
        "team": team_code.upper(),
        "wins": wins,
        "losses": losses,
        "ties": ties,
    }

    conference_table: Dict[str, List[Dict[str, any]]] = {}
    for division, clubs in DIVISIONS.items():
        division_table: List[Dict[str, any]] = []
        for club in clubs:
            if club == team_code.upper():
                division_table.append(standings)
            else:
                division_table.append(
                    {
                        "team": club,
                        "wins": rng.randint(3, 13),
                        "losses": rng.randint(3, 13),
                        "ties": 0,
                    }
                )
        conference_table[division] = division_table

    return {
        "team": team_code.upper(),
        "standings": standings,
        "schedule": games,
        "conference": conference_table,
    }
