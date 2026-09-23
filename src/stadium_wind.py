"""Q1: did the new Highmark Stadium actually cut the wind?

The architects claim the new bowl cuts field-level wind 50-67% vs the old
stadium. That's CFD modeling, not measurement -- there's no field-level
anemometer data anywhere. So the test is whether the football moved.

This file holds the Q1 scorer (q1_table, what the logged prediction is
graded on). The wind -> deep-ball model fit on every outdoor stadium
2016-2025 goes here too once src/weather.py covers them.

Scoring definitions, fixed before any 2026 numbers were read:
  - Home = games actually played at BUF00 (drops the 2022 Detroit "home"
    game and 2023 London). Regular season + playoffs: January wind is the
    point, so the playoff games stay in.
  - Deep ball = pass attempt with air_yards >= 20. Success = nflverse
    `success` (EPA > 0). Sacks have no air yards, so they're out.
  - FG make rate: blocked counts as a miss.
  - Away games are the control. A better offense or a new kicker moves
    home AND away numbers; a stadium only moves home. home_minus_away is
    the change at home net of the change on the road -- the closest thing
    to a stadium effect this data can give. The logged prediction is
    scored on the `home` rows.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import polars as pl

from off_script import interval
from opponent_adjustment import N_BOOT
from weather import NEW_HIGHMARK_SEASON

DB = Path("data/db/bills.duckdb")
TEAM = "BUF"
HOME_STADIUM = "BUF00"
DEEP_AIR_YARDS = 20


def load_bills_kicks_and_deep_balls(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """One row per Bills deep attempt or FG attempt, tagged venue and era."""
    query = """
        SELECT
            game_id, season,
            CASE
                WHEN home_team = ? AND stadium_id = ? THEN 'home'
                WHEN away_team = ? THEN 'away'
            END AS venue,
            field_goal_attempt = 1 AS is_fg,
            CASE WHEN field_goal_attempt = 1 THEN field_goal_result = 'made'
                 ELSE success = 1 END AS hit
        FROM pbp
        WHERE posteam = ?
          AND season_type IN ('REG', 'POST')
          AND (
                field_goal_attempt = 1
                OR (pass_attempt = 1 AND air_yards >= ? AND success IS NOT NULL)
          )
    """
    df = pl.from_arrow(con.execute(query, [TEAM, HOME_STADIUM, TEAM, TEAM, DEEP_AIR_YARDS]).arrow())
    return df.filter(pl.col("venue").is_not_null()).with_columns(
        pl.when(pl.col("season") >= NEW_HIGHMARK_SEASON).then(pl.lit("new")).otherwise(pl.lit("old")).alias("era"),
        pl.when(pl.col("is_fg")).then(pl.lit("fg_pct")).otherwise(pl.lit("deep_success")).alias("stat"),
    )


def _rate_draws(per_game: pl.DataFrame, n_boot: int, seed: int) -> np.ndarray:
    """Game-clustered bootstrap of a pooled rate (sum hits / sum attempts)."""
    k, n = per_game["k"].to_numpy().astype(float), per_game["n"].to_numpy().astype(float)
    idx = np.random.default_rng(seed).integers(0, len(n), size=(n_boot, len(n)))
    with np.errstate(invalid="ignore", divide="ignore"):
        return k[idx].sum(axis=1) / n[idx].sum(axis=1)


def q1_table(con: duckdb.DuckDBPyConnection, n_boot: int = N_BOOT) -> pl.DataFrame:
    """Old vs new stadium era, home and away, for deep-ball success and FG%.

    One row per (stat, venue) plus a home_minus_away row per stat. Values
    are rates; change is in rate units (0.03 = +3 percentage points).
    """
    per_game = (
        load_bills_kicks_and_deep_balls(con)
        .group_by("stat", "venue", "era", "game_id")
        .agg(pl.col("hit").sum().alias("k"), pl.len().alias("n"))
    )
    rows, change_draws, change_games = [], {}, {}
    for seed, ((stat, venue), cell) in enumerate(sorted(per_game.group_by("stat", "venue"), key=lambda x: x[0])):
        row: dict[str, object] = {"stat": stat, "venue": venue}
        draws, games = {}, {}
        for era in ("old", "new"):
            g = cell.filter(pl.col("era") == era)
            games[era] = g.height
            draws[era] = _rate_draws(g, n_boot, seed=2 * seed + (era == "new")) if g.height else np.array([np.nan])
            lo, hi = interval(draws[era], games[era])
            row |= {
                era: g["k"].sum() / g["n"].sum() if g.height else None,
                f"{era}_lo": lo, f"{era}_hi": hi,
                f"attempts_{era}": int(g["n"].sum()), f"games_{era}": games[era],
            }
        row["change"] = row["new"] - row["old"] if row["new"] is not None else None
        change_draws[(stat, venue)] = draws["new"] - draws["old"]
        change_games[(stat, venue)] = min(games.values())
        row["change_lo"], row["change_hi"] = interval(change_draws[(stat, venue)], change_games[(stat, venue)])
        rows.append(row)

    for stat in ("deep_success", "fg_pct"):
        home = next(r for r in rows if r["stat"] == stat and r["venue"] == "home")
        away = next(r for r in rows if r["stat"] == stat and r["venue"] == "away")
        diff = change_draws[(stat, "home")] - change_draws[(stat, "away")]
        lo, hi = interval(diff, min(change_games[(stat, "home")], change_games[(stat, "away")]))
        both = home["change"] is not None and away["change"] is not None
        rows.append({"stat": stat, "venue": "home_minus_away",
                     "change": home["change"] - away["change"] if both else None,
                     "change_lo": lo, "change_hi": hi})
    return pl.DataFrame(rows, infer_schema_length=None).sort("stat", "venue")


def _check() -> None:
    # every game 1-for-2: every bootstrap draw must be exactly 0.5
    fake = pl.DataFrame({"k": [1] * 8, "n": [2] * 8})
    assert np.allclose(_rate_draws(fake, 100, 0), 0.5)
    # pooled, not averaged per game: 1/1 and 0/3 pools to 0.25, not 0.5
    two = pl.DataFrame({"k": [1, 0], "n": [1, 3]})
    assert np.isclose(two["k"].sum() / two["n"].sum(), 0.25)


def _demo() -> None:
    _check()
    con = duckdb.connect(str(DB), read_only=True)
    try:
        table = q1_table(con)
    finally:
        con.close()
    with pl.Config(tbl_rows=-1, tbl_cols=-1, float_precision=3, tbl_width_chars=200):
        print(table)


if __name__ == "__main__":
    _demo()
