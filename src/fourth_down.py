"""Fourth-down decision audit.

Q2: is Joe Brady (Bills OC as of 2026) a better fourth-down decision maker
than the McDermott-era Bills? See docs/plan-of-action.md.

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
import polars as pl

DB = Path("data/db/bills.duckdb")
MCDERMOTT_START = 2017  # Rex Ryan/Anthony Lynn through 2016; McDermott hired 2017
BRADY_START = 2026      # Joe Brady's first season as Bills OC


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


def team_summary(decisions: pl.DataFrame) -> pl.DataFrame:
    """Leaguewide benchmark: one row per team, ranked by average WP cost."""
    return (
        decisions.group_by("posteam")
        .agg(
            pl.len().alias("n_fourth_downs"),
            pl.col("followed_baseline").mean().alias("pct_followed_baseline"),
            pl.col("wp_cost_pts").mean().alias("avg_wp_cost_pts"),
            pl.col("wp_cost_pts").sum().alias("total_wp_cost_pts"),
        )
        .sort("avg_wp_cost_pts")
    )


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
    return (
        buf.group_by("era")
        .agg(
            pl.len().alias("n"),
            pl.col("followed_baseline").mean().alias("pct_followed_baseline"),
            pl.col("wp_cost_pts").mean().alias("avg_wp_cost_pts"),
        )
        .sort("era")
    )


def _demo() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        decisions = load_decisions(con)
    finally:
        con.close()

    assert decisions.height > 0, "no 4th-down plays joined -- check the nfl4th_go_boost join"
    assert set(decisions["actual_decision"].unique()) <= {"go", "punt", "field_goal"}
    assert decisions.filter(pl.col("posteam") == "BUF").height > 0, "no Bills 4th downs found"

    with pl.Config(tbl_rows=32):
        print("=== leaguewide, most to least aggressive-and-correct ===")
        print(team_summary(decisions))
        print("\n=== Bills: McDermott era vs Brady 2026 ===")
        print(bills_era_summary(decisions))


if __name__ == "__main__":
    _demo()
