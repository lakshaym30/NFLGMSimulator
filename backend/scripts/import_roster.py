"""CLI script to load roster + contract JSON into the SQLite database.

The roster file can be a single-team snapshot or the full league dump produced
by `fetch_nfl_rosters.py`. Contracts may be Cardinals-only JSON (with `player_id`
fields) or a league-wide export converted via `convert_contracts_csv.py`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Cardinals roster + contract data into the local database."
    )
    parser.add_argument(
        "--roster",
        required=True,
        type=Path,
        help="Path to roster JSON (single team or league-wide file from fetch_nfl_rosters.py)",
    )
    parser.add_argument(
        "--contracts",
        required=True,
        type=Path,
        help="Path to contracts JSON (team-specific or league-wide export JSON)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Override DATABASE_URL env var for this import run.",
    )
    return parser.parse_args()


def ensure_backend_on_path() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))


def main() -> None:
    args = parse_args()
    ensure_backend_on_path()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.core.config import settings
    from app.db.session import SessionLocal, engine
    from app.ingest.service import import_dataset, load_payload, reset_database

    roster_payload = load_payload(args.roster)
    contracts_payload = load_payload(args.contracts)

    reset_database(engine)

    with SessionLocal() as session:
        summary = import_dataset(session, roster_payload, contracts_payload)

    print(
        f"Imported {summary.players} players with {summary.contracts} contracts "
        f"into {settings.database_url}"
    )


if __name__ == "__main__":
    main()
