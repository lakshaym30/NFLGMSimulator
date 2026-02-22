# Vision & Constraints — Cardinals GM Simulator

## Purpose
Give a solo Arizona Cardinals fan the ability to experiment with roster, contract, and cap moves in an environment that mirrors the real 2024 team as closely as possible without requiring league-wide data feeds or heavyweight infrastructure.

## Audience
- **Primary**: technically inclined Cardinals fans who want to understand cap implications of moves and explore “what-if” rebuild scenarios.
- **Secondary**: future version of me studying roster-building decisions or extending the sim to other teams.

## Goals
- Mirror the real Cardinals 90-man roster (plus PS/IR) for a chosen `as_of_date` with accurate biographical and contract details.
- Provide transparent cap calculations (base, bonuses, proration, dead money) for each player.
- Allow basic transactions (sign, release, restructure, simple trades) with instant validation feedback.
- Run entirely on a developer laptop with Python + Node installed; no Docker or external services required.
- Maintain league-wide roster + contract data for reference so future features can expand beyond the Cardinals without reworking the pipeline.

## Non-Goals (Phase 0–2)
- Simulating full league dynamics (other teams’ AI behavior, standings, schedules).
- Real-time data sync or licensed paid APIs.
- Multiplayer or authenticated user accounts.
- Mobile-optimized UI polish or advanced 3D visualizations.

## Realism Boundaries
- Contract math approximates CBA rules for prorated bonuses, void years, and pre/post June 1 handling but will not cover niche clauses (incentive offsets, injury settlements) initially.
- Cap figures target ±0.5 % accuracy versus public references; discrepancies will be documented.
- Draft pick values and scouting grades will be stubbed or fictional until later phases.

## Data Sources & Update Cadence
- **Roster & player bios**: manually export CSV/JSON from official team site (azcardinals.com roster) weekly or when significant moves occur.
- **Contract & cap data**: Spotrac or OverTheCap public tables copied into `data/contracts_YYYYMMDD.json` with attribution noted in commits.
- **Depth chart & statuses**: Cardinals PR depth chart releases or AZ media guides, refreshed monthly.
- Each ingest stores `source_name`, `source_url`, and `as_of_date`. Scripts will refuse to load stale files without explicit override.

## Risks & Mitigations
- **Data accuracy drift**: maintain changelog in `docs/data-log.md`; schedule manual audit twice per month.
- **Scope creep**: any new feature request must reference the lean roadmap and specify a measurable win before work starts.
- **Legal/usage limits**: use only publicly viewable information, attribute sources in UI, and avoid redistributing raw paid data.

## Definition of Success (Phase 2)
By the end of Phase 2, the project has a SQLite database populated from the documented sources, matching roster counts and contract samples, with scripts and docs enabling anyone to recreate the dataset on their machine.
