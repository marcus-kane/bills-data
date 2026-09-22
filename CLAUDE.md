# CLAUDE.md

Context for Claude Code working in this repo. Read `docs/plan-of-action.md` for the
full reasoning; this file is the operating summary.

## What this is

A public NFL analytics project on the 2026 Buffalo Bills, built by Marcus Kane
(data science sophomore, UNL) as a portfolio piece aimed at golf/sports analytics
and content work. It ships weekly from September 2026 through January 2027.

Four questions, each falsifiable:

1. Did the new Highmark Stadium actually cut the wind? (deep-ball outcomes vs
   interpolated wind; architects claim 50–67% field-level reduction)
2. Is Joe Brady a better fourth-down decision maker than Sean McDermott?
   (every 4th down vs an EPA-optimal baseline)
3. Is Brady's design reducing Josh Allen's need to freelance?
   (FTN out-of-pocket rate; on-script vs off-script efficiency gap)
4. Is Leonhard's defense better, or is the schedule easier?
   (opponent adjustment — infrastructure for 1–3, built second)

## Stack

- Python 3.12 in `.venv`. `nfl_data_py`, `polars`, `duckdb`, `pyarrow`, `meteostat`,
  `matplotlib`. Quarto for the site.
- Data lands as parquet in `data/raw/`, loads into one DuckDB file at `data/db/bills.duckdb`.
- `refresh.py` re-pulls only the current season. Keep it working — the pipeline is
  the point, not the notebooks.
- `nfl4th` is R-only. Default to reading its precomputed parquet
  (`load_4th_pbp(fast = TRUE)`, 2014+) from the nflverse release rather than
  shelling out to R. Only reach for R if that route fails.

## Data facts worth not re-learning

- pbp weather is **one reading per game**, often missing, from the nearest airport
  station. New Highmark is among the furthest NFL stadiums from any station.
  Use `meteostat` (METAR + ISD-Lite) to interpolate hourly, ~3–4 readings/game.
- There is **no wind direction relative to field orientation** in any public source.
  Field is roughly north–south; convert station bearing to head/tail/cross yourself.
- NGS is **player-week aggregate**, not per play. Time-to-throw per play does not
  exist publicly. Do not propose analyses that need it.
- FTN charting is **per play, 2022+**, updated 4×/day in season. It carries
  `is_qb_out_of_pocket`, `read_thrown`, `n_pass_rushers`, `is_throwaway`,
  motion, play action, RPO, screen, QB alignment. This is what makes Q2 and Q3 work.
- Participation data (personnel, coverage, man/zone) is **postseason only** — useless
  for in-season weekly posts.
- n for the new stadium this season is ~9–10 home games. Nothing stadium-specific
  can be fit on that; fit on all outdoor stadiums 2016–2025 and treat 2026 Highmark
  as an out-of-sample test.

## House rules

- **Intervals, not point estimates.** Every number gets uncertainty attached.
- **Name what the model doesn't know.** Fourth-down calls especially: injuries,
  kicker, wind at that moment, timeouts, personnel. Saying so is part of doing it well.
- **Predictions before analysis.** `predictions.md`, timestamped, never edited after
  the fact. Score the misses in January.
- **Out-of-sample validation is not optional** for the opponent adjustment: does
  adjusted EPA predict next week better than raw EPA? Report the number.
- **Notebooks are scratch.** Nothing ships from `notebooks/`. Analysis that matters
  moves into `src/` with a function signature.
- Writing keeps Marcus's voice — direct, opinionated, no hedged generalities.
  Football interpretation and statistics live in the same document.

## Current state

Phase 0 — the spine. `refresh.py` is a stub with the structure laid out and
`NotImplementedError` in `pull()` and `build_db()`. Next: wire up the nfl_data_py
pulls and the DuckDB load, then Phase 1 (fourth-down audit, the fastest win).

Open decisions, unresolved:
- Project name, and whether it gets its own domain
- Hand-charting variable: wind direction relative to throw, or motion type
- All-Python-with-an-R-shim, or accept R for the modeling steps
