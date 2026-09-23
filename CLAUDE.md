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
- `nfl4th` is R-only. Its precomputed decisions ship as per-season `.rds` on the
  nflverse release (no parquet upstream); `refresh.py` reads them with `pyreadr`.
  No R needed.

## Data facts worth not re-learning

- pbp weather is **one reading per game**, often missing, from the nearest airport
  station. New Highmark is among the furthest NFL stadiums from any station.
  Use `meteostat` (METAR + ISD-Lite) to interpolate hourly, ~3–4 readings/game.
- There is **no wind direction relative to field orientation** in any public source.
  Old Highmark's field runs **302°/122° (NW–SE), not north–south**. Field headings
  for every stadium are in `data/reference/stadiums.csv` (source in its README).
  The new Highmark's heading is unmeasured: `NEW_HIGHMARK_HEADING` in `src/weather.py`.
- nflverse `schedules.gametime` is **always US Eastern**, whatever the venue.
- NGS is **player-week aggregate**, not per play. Time-to-throw per play does not
  exist publicly. Do not propose analyses that need it.
- FTN charting is **per play, 2022+**, updated 4×/day in season. It carries
  `is_qb_out_of_pocket`, `read_thrown`, `n_pass_rushers`, `is_throwaway`,
  motion, play action, RPO, screen, QB alignment. This is what makes Q2 and Q3 work.
- FTN charts in batches, so the latest week is often partial. `src/off_script.py`
  drops any game under 95% charted rather than using a partial chart.
- `meteostat` is on the 2.x API. Wind direction must be blended as u/v vectors,
  never averaged as degrees (`src/weather.py`).
- nflverse `schedules.home_coach/away_coach` still says McDermott for BUF 2026.
  It's stale: Brady was named head coach Jan 27, 2026. Don't trust that field for
  era splits; split on season.
- Opponent adjustment uses `ALPHA = 300` (the walk-forward winner). Until Sept 2026
  `current_ratings()` silently defaulted to 30; anything computed before then used it.
- Game-clustered bootstrap intervals are NaN below `MIN_GAMES = 4` (a team or QB
  with 2 games has 3 distinct resamples). Bands stay optimistic until ~10 games.
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

Phases 0–2 done: `refresh.py` pipeline, fourth-down audit + live Brady tracker
(`src/fourth_down.py`, `weekly_tracker.py`), opponent-adjusted EPA
(`src/opponent_adjustment.py`).

In progress:
- Phase 3: `src/off_script.py` computes Allen's out-of-pocket rate and on/off-script
  gap with game-clustered bootstrap intervals. `era_table()` splits Allen by
  play-caller: Dorsey OC (2022–Wk 10 2023), Brady OC (Wk 11 2023–2025), Brady
  HC (2026). Brady called plays from late 2023, so "2022–25 vs 2026" is not
  McDermott-vs-Brady. Use `off_rate_vs_league`: FTN's league-wide rate drifts up.
- Phase 4: `src/weather.py` pulls hourly wind for every outdoor game 2016+ into
  the `weather` table via `refresh.py`, with along/cross components per play
  from each stadium's field heading. `src/stadium_wind.py` has the Q1 scorer
  (home and away, old vs new). Still needed: the new Highmark's heading
  (measure it), then the wind -> deep-ball model on all outdoor stadiums.

Weekly: `python refresh.py && python weekly_tracker.py` writes every table the
post needs to `data/derived/`, including the numbers each logged prediction is
scored on.

Not started: first weekly post, hand-charting codebook, Phase 5.

Open decisions, unresolved:
- Project name, and whether it gets its own domain
- Hand-charting variable: wind direction relative to throw, or motion type
