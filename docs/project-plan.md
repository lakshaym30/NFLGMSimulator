# Cardinals GM Simulator — Lean Project Plan

Keeping the experience lightweight means building only what is necessary for a solo GM sandbox. These phases focus on host-native tooling (Python, SQLite, Vite/Next.js) so development never requires Docker or managed cloud services until the simulation proves useful.

## Guiding Principles
- Prefer plain files (JSON/CSV) and scripts before introducing external services.
- Every phase should be verifiable with a CLI command (`pytest`, `uvicorn`, `npm run dev`).
- Add new dependencies only when an existing manual process becomes painful.
- Always record the roster source and `as_of_date` alongside stored data for traceability.

## Phases & Acceptance Criteria

### Phase 0 — Vision & Constraints
- Deliverables: concise one-pager capturing audience, goals, realism boundaries, manual data sources, risks.
- Acceptance: document committed to `docs/vision.md`; it names at least one roster+contract source with an update cadence and explicitly lists non-goals (e.g., no full-league sim yet).

### Phase 1 — Minimal Dev Setup
- Deliverables: FastAPI skeleton backed by SQLite, React/Vite (or Next.js) scaffold, shared `.env.example`, and clear run instructions.
- Acceptance: `pip install -r backend/requirements.dev.txt` followed by `uvicorn app.main:app --reload` works; `npm install && npm run dev` works; README documents both commands plus the health check URL.

### Phase 2 — Data & Schema
- Deliverables: canonical schema (players, contracts, contract years, roster status) and raw data files under `data/`. League-wide rosters sourced via `backend/scripts/fetch_nfl_rosters.py` (ESPN public API) plus `backend/scripts/build_team_roster.py` to slice Cardinals-only payloads. Contract exports normalized with `backend/scripts/convert_contracts_csv.py`.
- Acceptance: running `python backend/scripts/import_roster.py --roster data/cardinals_roster_<date>.json --contracts data/cardinals_contracts_<date>.json` rebuilds SQLite from scratch; roster count matches source for the recorded date; five contracts spot-checked against the reference cap sheet deviate <0.5%. `python backend/scripts/fetch_nfl_rosters.py` + `python backend/scripts/build_team_roster.py --team ARI` succeed without API keys and capture all 32 teams with metadata before slicing. `python backend/scripts/convert_contracts_csv.py --csv data/contracts.csv` produces a league snapshot with source metadata for audits.

### Phase 3 — Core API
- Deliverables: `/health`, `/teams/ari/roster`, `/players/{id}`, `/teams/ari/cap` endpoints plus unit tests for serializers and cap math helpers.
- Acceptance: `pytest` passes; API responses stay under 150 ms on seeded data; OpenAPI docs reachable at `/docs`; failing validations return helpful 4xx messages.

### Phase 4 — Frontend MVP
- Deliverables: roster table, player detail drawer/page, cap summary visualization implemented in the frontend scaffold with direct fetch calls.
- Acceptance: page load <1.5 s in dev mode; selecting a player displays bio + contract table; cap summary matches backend calculations; ESLint/TypeScript clean.

### Phase 5 — Transactions & Cap Mechanics
- Deliverables: simple transaction engine (sign, release, trade) with in-memory previews and persisted results, plus a “what-if” endpoint/UI widget.
- Acceptance: roster limit (90/53) and cap room enforced; cap-negative moves reject with reasons; releasing a player updates savings/dead money correctly for at least three sample contracts; integration test suite (`pytest -k transactions`) passes.

### Phase 6 — Enhancements (Iterative)
- Deliverables: UX polish and realism upgrades that build on the core sim (user-facing GM primer, richer roster analytics, etc.).
- Acceptance: Each enhancement must articulate a measurable outcome (e.g., “contract primer accessible via `/gm-basics`”, “cap summary exposes Top-10 hits“) and include manual verification notes since automated tests are skipped.

## Lightweight Workflow Checklist
- `make install` (or run the pip/npm commands manually).
- `make run-backend` → visit `http://localhost:8000/health`.
- `make run-frontend` → visit the roster screen.
- `make lint` keeps Ruff + ESLint happy.

When these steps feel cumbersome again, reassess and decide whether it is time to introduce Docker or hosted environments.
