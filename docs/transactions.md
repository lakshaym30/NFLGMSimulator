# Phase 5 — Transactions & Cap Mechanics

Our goal for this phase is to let a user perform realistic front-office moves for any franchise with clear cap visibility. The first milestone will cover signing, releasing, and trading players with deterministic previews before persisting any changes.

## Scope for the initial milestone
- **Supported moves:** veteran signing (FA), player release/waive (pre/post June 1), and player-for-player or player-for-pick trades.
- **Execution flow:** every move goes through a `POST /transactions/preview` call that returns the projected roster/cap deltas. If the user accepts, a `POST /transactions` call commits it.
- **Persistence:** transactions are stored with an audit trail so we can rebuild historical cap states or undo/replay later.
- **Cap math:** we focus on base salary + signing bonus proration. Future enhancements (void years, incentives, etc.) stay out-of-scope for now but the model should be extensible.

## Data model changes
- `CapYear`: captures cap limits per league year (default 2024: \$255.4M, but configurable via settings).
- `ContractYear`: already exists; we’ll backfill cap_hit/dead_money fields if the ingest didn’t set them.
- `Transaction`: top-level log with `id`, `team_id`, `type`, `status`, `executed_at`, `notes`, `created_by`.
- `TransactionLeg`: per-team effect for a transaction (because trades touch two teams). Records `cap_delta`, `player_ids`, and roster counts before/after.
- `TransactionAudit`: JSON blob for request payload + calc results to make undo possible without re-simulating.

## Cap math helpers
All helpers will live under `app/services/cap.py`.

1. `annual_proration(contract, season)` — divides total signing bonus over remaining proration years.
2. `cap_hit(contract_year)` — base + proration + roster/workout bonuses.
3. `release_savings(contract, season, post_june_1)` — returns `(savings, dead_money)` using:
   - Pre June 1: accelerate all remaining proration + current guaranteed cash.
   - Post June 1: current-year proration hits this season; future proration hits next.
4. `trade_savings(...)` — same as release, but the acquiring team takes the remaining base salaries and guarantees (no signing proration).
5. `signing_cap_hit(new_contract, season)` — first-year cap hit is base + proration + any bonuses.

Each helper returns rounded dollars (no cents) so UI numbers line up with spreadsheets.

## Validation rules
1. **Cap room:** `team.cap_space >= required_cap` after the move. If not, error includes the shortfall and a hint (“Free \$4.2M by releasing X” once heuristics exist).
2. **Roster limit:** enforce 90 players in offseason; 53 during season (toggle by env or date).
3. **Trade counterpart:** both teams must satisfy cap + roster rules. If the partner fails, reject with a structured reason.
4. **Player state:** can’t release/trade players already cut or traded within the current sim day; we’ll enforce via a `players.status` check.

## API surface (JSON)

### POST `/transactions/preview`
```json
{
  "team_code": "ARI",
  "type": "release",
  "payload": {
    "player_id": 123,
    "post_june_1": false
  }
}
```
Response:
```json
{
  "allowed": true,
  "cap_delta": -4800000,
  "cap_space_after": 12500000,
  "dead_money": 2600000,
  "notes": ["Saves $4.8M, adds $2.6M dead money"]
}
```

Other payload options:
- `sign`: `{ "player_id": 456, "contract_id": 789 }`
- `trade`: `{ "player_ids": [1], "partner_team": "PHI", "partner_player_ids": [9], "pick_compensation": [] }`

### POST `/transactions`
Same request as preview plus a `preview_id` or the preview payload echoed back. Backend re-runs validation before committing.

### GET `/transactions?team=ARI`
Returns the log (for future UI). Not required for the first drop but simple to expose using the Transaction table.

## UI implications
- Add a **“Transactions” drawer** beneath the player panel with tabs for Release, Sign, Trade.
- Each tab calls `/transactions/preview` on change and displays the savings/dead money summary inline before enabling “Commit”.
- After committing, refresh the roster/cap panels via existing fetchers.

## Acceptance checklist for Phase 5
1. Release/sign/trade previews return deterministic cap math for at least three real contracts (spot-check vs OTC/Spotrac within 0.5%).
2. Cap-negative moves return 400 with a clear message.
3. `/transactions` writes an audit row that captures inputs + computed deltas.
4. Frontend can release a player end-to-end (preview + commit) and see the roster/cap update without reload.
5. README gains a “Transactions” section describing the commands to simulate a release and where numbers come from.

Future iterations (not part of this milestone):
- In-season roster limits (53/46 active) with PS/IR rules.
- Prospective restructuring/extension UI with sliders.
- Automated suggestion engine for clearing cap space.
