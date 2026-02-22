# NFL GM Simulator

Personal sandbox to explore what it feels like to run any NFL front office (the Arizona Cardinals were just the first test case). The stack is intentionally lightweight—FastAPI + SQLite on the backend, Next.js + Tailwind on the frontend—with everything running directly on the host machine (no Docker required).

## Getting Started

1. Copy environment defaults (optional but keeps overrides tidy):
   ```bash
   cp .env.example .env
   ```
2. Install dependencies:
   ```bash
   make install
   ```
3. Run the backend:
   ```bash
   make run-backend
   # visit http://localhost:8000/health
   ```
4. In a second terminal, run the frontend:
   ```bash
   make run-frontend
   # visit http://localhost:3000
   ```

Set `CAP_YEAR` in your `.env` file if you want the cap tables to use a specific league year (defaults to the current calendar year).

## Import sample roster data

```bash
python backend/scripts/import_roster.py \
  --roster data/cardinals_roster_2024-06-01.json \
  --contracts data/cardinals_contracts_2024-06-01.json
```

Edit the JSON files under `data/` when you capture new roster snapshots—the script will rebuild `nfl.db` each time.

### Pull fresh league-wide rosters

Use the ESPN public roster API (no key required) to capture the latest 32-team snapshot:

```bash
python backend/scripts/fetch_nfl_rosters.py --output data/nfl_rosters_$(date +%F).json
```

Slice that data down to the Cardinals-only file the importer expects:

```bash
python backend/scripts/build_team_roster.py \
  --league-file data/nfl_rosters_$(date +%F).json \
  --team ARI \
  --output data/cardinals_roster_$(date +%F).json
```

Then refresh SQLite with either the full league file or the sliced Cardinals roster (alongside a matching contracts file). Replace `$(date +%F)` with whatever date stamp you used when creating the files (for example `2026-02-21`):

```bash
python backend/scripts/import_roster.py \
  --roster data/nfl_rosters_$(date +%F).json \  # or cardinals_roster_*.json
  --contracts data/contracts_league_$(date +%F).json
```

If your contract data starts as a CSV export (Spotrac/OTC, etc.), normalize it first:

```bash
python backend/scripts/convert_contracts_csv.py \
  --csv data/contracts.csv \
  --output data/contracts_league_$(date +%F).json \
  --as-of-date $(date +%F) \
  --source-name "Spotrac export" \
  --source-url "https://www.spotrac.com/nfl/" \
  --start-year 2026
```

Use the resulting JSON as the authoritative snapshot—the importer will match players by name/team, so you can feed the entire league file directly.

Each script records metadata about where the data came from so you can audit updates later.

## Transactions

The API now supports simple sign/release/trade workflows with preview+commit semantics. Reference payloads live in `docs/transactions.md`.

Preview a release:

```bash
curl -X POST http://localhost:8000/transactions/preview \
  -H "Content-Type: application/json" \
  -d '{"team_code":"ARI","type":"release","payload":{"player_id":123}}'
```

Commit the move (re-validation happens server-side):

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"team_code":"ARI","type":"release","payload":{"player_id":123}}'
```

Signing/new-player payloads require `full_name`, `position`, and `apy`; trades need `send_player_ids`, `receive_player_ids`, and `partner_team_code`. Every transaction persists an audit row in the `transactions` table so the cap history can be replayed later.

Undo a release (only releases are supported right now):

```bash
curl -X POST http://localhost:8000/transactions/<transaction_id>/undo
```

> Re-running `backend/scripts/import_roster.py` will rebuild SQLite from scratch, so capture the database before you wipe it if you care about previous transactions.

### Frontend flow

1. Start the backend: `DATABASE_URL=sqlite:///./nfl.db PYTHONPATH=backend uvicorn app.main:app --reload`.
2. Run `cd frontend && npm run dev` and open `http://localhost:3000`.
3. Pick a team/player, scroll to the **Release Player** panel, and hit **Preview Release**. The UI displays cap savings/dead money; clicking **Commit Release** calls `/transactions` and refreshes the roster/cap widgets automatically. Use the **Undo release** button in the ledger if you need to restore a cut player.
4. Visit `/market` for the AI-driven free agency/trade board, `/draft` for the scouting simulator, and `/season` for the schedule/standings sandbox.

## Tests & Linting

```bash
cd backend && pytest
make lint
```

Ruff checks the backend and ESLint/TypeScript cover the frontend.

## Project Layout

- `backend/` – FastAPI app, configuration, and database session wiring (defaults to `sqlite:///./nfl.db`).
- `backend/scripts/` – Utility scripts for fetching league rosters, slicing team data, and importing into SQLite.
- `frontend/` – Next.js (App Router) UI scaffold with Tailwind CSS.
- `data/` – Source-of-truth roster + contract JSON snapshots with attribution.
- `docs/project-plan.md` – Lean phased plan with acceptance criteria; see `docs/vision.md` for scoped goals.
- `/gm-basics` – Frontend primer that explains the rules the sim approximates.
- `infra/` – Placeholder for future deployment/infra artifacts once the project outgrows local scripts.
