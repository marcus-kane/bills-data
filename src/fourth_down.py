"""Fourth-down decision audit.

Q2: is Joe Brady (Bills head coach and play-caller from 2026; McDermott was
fired Jan 2026) a better fourth-down decision maker than the McDermott-era Bills? See docs/plan-of-action.md.

The baseline isn't raw EPA -- it's the nfl4th win-probability model (go_wp /
punt_wp / fg_wp per play, from the nflverse `nfl4th` R package's precomputed
release). "EPA-optimal" in CLAUDE.md is loose language for this; be precise
about it in anything published. The model doesn't know injuries, the kicker
that week, wind at that moment, timeouts, or personnel -- every "wrong call"
claim below is contestable on those grounds, and that's worth saying out loud
next to the numbers, not just once here.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import polars as pl

from opponent_adjustment import MIN_GAMES

DB = Path("data/db/bills.duckdb")
N_BOOT = 2000
MCDERMOTT_START = 2017  # Rex Ryan/Anthony Lynn through 2016; McDermott hired 2017
BRADY_START = 2026      # Joe Brady's first season as Bills head coach


def load_decisions(con: duckdb.DuckDBPyConnection, team: str | None = None) -> pl.DataFrame:
    """Every 4th-down play joined to its nfl4th win-probability baseline.

    One row per 4th down with the decision actually made, the WP-optimal
    decision, and the WP cost of the gap between them (percentage points).
    """
    where = "p.down = 4 AND (p.punt_attempt = 1 OR p.field_goal_attempt = 1 OR p.rush_attempt = 1 OR p.pass_attempt = 1)"
    params: list[str] = []
    if team:
        where += " AND p.posteam = ?"
        params.append(team)

    query = f"""
        SELECT
            p.game_id, p.season, p.week, p.posteam, p.defteam,
            p.qtr, p.down, p.ydstogo, p.yardline_100, p.score_differential,
            p.punt_attempt, p.field_goal_attempt, p.rush_attempt, p.pass_attempt,
            p.epa,
            g.go_wp, g.punt_wp, g.fg_wp, g.go_boost
        FROM pbp p
        JOIN nfl4th_go_boost g ON p.game_id = g.game_id AND p.play_id = g.play_id
        WHERE {where}
    """
    df = pl.from_arrow(con.execute(query, params).arrow())

    df = df.with_columns(
        pl.when(pl.col("punt_attempt") == 1).then(pl.lit("punt"))
        .when(pl.col("field_goal_attempt") == 1).then(pl.lit("field_goal"))
        .otherwise(pl.lit("go"))
        .alias("actual_decision"),
        pl.max_horizontal("go_wp", "punt_wp", "fg_wp").alias("best_wp"),
    )
    df = df.with_columns(
        pl.when(pl.col("best_wp") == pl.col("go_wp")).then(pl.lit("go"))
        .when(pl.col("best_wp") == pl.col("punt_wp")).then(pl.lit("punt"))
        .otherwise(pl.lit("field_goal"))
        .alias("best_decision"),
        pl.coalesce(
            pl.when(pl.col("actual_decision") == "go").then(pl.col("go_wp")),
            pl.when(pl.col("actual_decision") == "punt").then(pl.col("punt_wp")),
            pl.when(pl.col("actual_decision") == "field_goal").then(pl.col("fg_wp")),
        ).alias("actual_wp"),
    )
    return df.with_columns(
        ((pl.col("best_wp") - pl.col("actual_wp")) * 100).alias("wp_cost_pts"),
        (pl.col("actual_decision") == pl.col("best_decision")).alias("followed_baseline"),
    )


def team_summary(
    decisions: pl.DataFrame,
    seasons: tuple[int, int] = (MCDERMOTT_START, BRADY_START - 1),
    n_boot: int = N_BOOT,
    seed: int = 0,
) -> pl.DataFrame:
    """Leaguewide benchmark over the McDermott years: one row per team, ranked
    by average WP cost, with 90% intervals on every rate. Includes Q2's metric
    (go rate on the model's go-calls) so the Bills' number has league context."""
    d = decisions.filter(pl.col("season").is_between(*seasons))
    go_call = pl.col("best_decision") == "go"
    return (
        d.group_by("posteam")
        .agg(
            pl.len().alias("n_fourth_downs"),
            pl.col("game_id").n_unique().alias("n_games"),
            pl.col("followed_baseline").sum().alias("n_followed"),
            pl.col("wp_cost_pts").mean().alias("avg_wp_cost_pts"),
            pl.col("wp_cost_pts").sum().alias("total_wp_cost_pts"),
            go_call.sum().alias("n_go_calls"),
            (pl.col("actual_decision") == "go").filter(go_call).sum().alias("went_on_go_calls"),
        )
        .with_columns(
            _wilson("n_followed", "n_fourth_downs", "pct_followed_baseline")
            + _wilson("went_on_go_calls", "n_go_calls", "go_rate_on_go_calls")
        )
        .drop("n_followed")
        .join(_cost_interval(d, n_boot, seed), on="posteam")
        .sort("avg_wp_cost_pts")
    )


def _cost_interval(d: pl.DataFrame, n_boot: int, seed: int, level: float = 0.9) -> pl.DataFrame:
    """90% game-clustered bootstrap on each team's average WP cost. Cost is
    mostly zeros with a few big misses, so the spread comes from which games
    land in the resample, not from individual calls."""
    rng = np.random.default_rng(seed)
    per_game = d.group_by("posteam", "game_id").agg(
        pl.col("wp_cost_pts").sum().alias("cost"),
        pl.col("wp_cost_pts").count().alias("n"),  # non-null, to match mean()
    )
    rows = []
    for g in per_game.partition_by("posteam"):
        cost, n = g["cost"].to_numpy(), g["n"].to_numpy()
        if len(n) < MIN_GAMES:
            lo, hi = np.nan, np.nan
        else:
            idx = rng.integers(0, len(n), size=(n_boot, len(n)))
            lo, hi = np.quantile(cost[idx].sum(1) / n[idx].sum(1), [(1 - level) / 2, (1 + level) / 2])
        rows.append((g["posteam"][0], lo, hi))
    return pl.DataFrame(rows, schema=["posteam", "avg_wp_cost_pts_lo", "avg_wp_cost_pts_hi"], orient="row")


def bills_era_summary(decisions: pl.DataFrame) -> pl.DataFrame:
    """McDermott (2017-2025) vs Brady (2026) fourth-down calls, Bills only."""
    buf = decisions.filter(
        (pl.col("posteam") == "BUF") & (pl.col("season") >= MCDERMOTT_START)
    ).with_columns(
        pl.when(pl.col("season") >= BRADY_START)
        .then(pl.lit(f"brady_{BRADY_START}"))
        .otherwise(pl.lit(f"mcdermott_{MCDERMOTT_START}_{BRADY_START - 1}"))
        .alias("era")
    )
    go_call = pl.col("best_decision") == "go"
    return (
        buf.group_by("era")
        .agg(
            pl.len().alias("n"),
            pl.col("followed_baseline").mean().alias("pct_followed_baseline"),
            pl.col("wp_cost_pts").mean().alias("avg_wp_cost_pts"),
            # Q2 as logged: when the model says go, how often do they go?
            go_call.sum().alias("n_go_calls"),
            (pl.col("actual_decision") == "go").filter(go_call).sum().alias("went_on_go_calls"),
        )
        .with_columns(_wilson("went_on_go_calls", "n_go_calls", "go_rate_on_go_calls"))
        .sort("era")
    )


def _wilson(k: str, n: str, name: str, z: float = 1.645) -> list[pl.Expr]:
    """Rate with a 90% Wilson interval. Fourth downs are few per game, so
    treating them as independent (no game clustering) costs little here."""
    p = pl.col(k) / pl.col(n)
    center = (p + z**2 / (2 * pl.col(n))) / (1 + z**2 / pl.col(n))
    half = z * ((p * (1 - p) / pl.col(n) + z**2 / (4 * pl.col(n) ** 2)).sqrt()) / (1 + z**2 / pl.col(n))
    return [p.alias(name), (center - half).alias(f"{name}_lo"), (center + half).alias(f"{name}_hi")]


def brady_tracker(decisions: pl.DataFrame) -> pl.DataFrame:
    """Every Brady-era (2026) Bills 4th down, in game order, with a running
    season-to-date cost so the gap can be watched week over week."""
    return (
        decisions.filter((pl.col("posteam") == "BUF") & (pl.col("season") >= BRADY_START))
        .sort(["week", "game_id"])
        .select(
            "season", "week", "game_id", "defteam", "qtr", "ydstogo", "yardline_100",
            "score_differential", "actual_decision", "best_decision",
            "wp_cost_pts", "followed_baseline", "epa",
        )
        .with_columns(
            pl.col("wp_cost_pts").cum_sum().round(2).alias("cum_wp_cost_pts"),
            ((pl.col("followed_baseline").cast(pl.Int32).cum_sum())
             / pl.int_range(1, pl.len() + 1) * 100).round(1).alias("cum_pct_followed_baseline"),
        )
    )


def _demo() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        decisions = load_decisions(con)
    finally:
        con.close()

    w = pl.DataFrame({"k": [5], "n": [10]}).select(_wilson("k", "n", "r")).row(0)
    assert np.allclose(w, (0.5, 0.2692, 0.7308), atol=1e-3), w  # hand-computed, z=1.645

    assert decisions.height > 0, "no 4th-down plays joined -- check the nfl4th_go_boost join"
    assert set(decisions["actual_decision"].unique()) <= {"go", "punt", "field_goal"}
    assert decisions.filter(pl.col("posteam") == "BUF").height > 0, "no Bills 4th downs found"

    # constant cost per game -> the bootstrap has nothing to vary, interval collapses
    flat = pl.DataFrame({"posteam": ["X"] * 10, "game_id": [str(i // 2) for i in range(10)], "wp_cost_pts": [1.0, 3.0] * 5})
    assert np.allclose(_cost_interval(flat, 200, 0).row(0)[1:], (2.0, 2.0))

    # the league table's Bills row must agree with the era table's McDermott row
    league = team_summary(decisions)
    buf = league.filter(pl.col("posteam") == "BUF").row(0, named=True)
    mcd = bills_era_summary(decisions).filter(pl.col("era").str.starts_with("mcdermott")).row(0, named=True)
    assert (buf["n_fourth_downs"], buf["n_go_calls"], buf["went_on_go_calls"]) == (mcd["n"], mcd["n_go_calls"], mcd["went_on_go_calls"]), (buf, mcd)

    with pl.Config(tbl_rows=32, tbl_cols=-1, tbl_width_chars=250):
        print(f"=== leaguewide {MCDERMOTT_START}-{BRADY_START - 1}, lowest avg WP cost first ===")
        print(league)
        print("\n=== Bills: McDermott era vs Brady 2026 ===")
        print(bills_era_summary(decisions))


if __name__ == "__main__":
    _demo()
