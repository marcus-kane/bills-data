"""Allen off-script: out-of-pocket rate and the on/off-script efficiency gap.

Q3: is Joe Brady's design reducing Josh Allen's need to freelance? If it is,
two things should move in 2026 vs 2022-2025: the share of dropbacks that
leave the pocket goes down, and the gap between on- and off-script EPA
matters less because fewer plays land on the off-script side.

Off-script = FTN `is_qb_out_of_pocket` OR pbp `qb_scramble`. That's a cleaner
definition than a time-to-throw threshold, which doesn't exist per play in
public data anyway (NGS is player-week aggregate). What this can't see:
*why* he left the pocket -- a designed rollout and a pocket collapse both
read as out-of-pocket. FTN doesn't split them. Say so next to the numbers.

Same judgment calls as opponent_adjustment.py, on purpose: REG season only,
garbage time out (wp in [0.05, 0.95]). EPA gets an opponent-adjusted twin by
subtracting the defense's season ridge rating.

Intervals are a game-clustered bootstrap: plays within a game share a
defense, a game plan and a weather, so resampling plays independently would
make the bands too narrow.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import polars as pl

from opponent_adjustment import WP_HIGH, WP_LOW, current_ratings

DB = Path("data/db/bills.duckdb")
ALLEN_ID = "00-0034857"
FTN_START = 2022
BRADY_START = 2026
MIN_DROPBACKS = 200  # league-table floor per QB-season; ignored for the current season
N_BOOT = 2000
MIN_FTN_COVERAGE = 0.95  # share of a game's dropbacks FTN must have charted


def load_dropbacks(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Every REG-season dropback 2022+ with FTN charting, one row per play.

    FTN charts in-season games in batches, so the latest week is often half
    done. Games under MIN_FTN_COVERAGE are dropped whole rather than letting
    a partial chart stand in for the game.
    """
    query = """
        WITH d AS (
            SELECT
                p.game_id, p.play_id, p.season, p.week, p.posteam, p.defteam,
                p.passer_id, p.passer, p.epa,
                f.nflverse_play_id IS NOT NULL AS charted,
                COALESCE(f.is_qb_out_of_pocket, FALSE) OR p.qb_scramble = 1 AS off_script
            FROM pbp p
            LEFT JOIN ftn f ON f.nflverse_game_id = p.game_id AND f.nflverse_play_id = p.play_id
            WHERE p.season >= ?
              AND p.season_type = 'REG'
              AND p.qb_dropback = 1
              AND p.epa IS NOT NULL
              AND p.passer_id IS NOT NULL
              AND p.wp BETWEEN ? AND ?
        )
        SELECT * EXCLUDE (charted) FROM d
        WHERE charted
          AND game_id IN (SELECT game_id FROM d GROUP BY game_id HAVING avg(charted::INT) >= ?)
    """
    df = pl.from_arrow(con.execute(query, [FTN_START, WP_LOW, WP_HIGH, MIN_FTN_COVERAGE]).arrow())

    # opponent adjustment: credit the offense for facing a good defense.
    # def_epa_adj is EPA allowed above average, so subtract it.
    ratings = pl.concat(
        current_ratings(con, season).select("team", "def_epa_adj").with_columns(pl.lit(season).alias("season"))
        for season in df["season"].unique().to_list()
    )
    return (
        df.join(ratings, left_on=["season", "defteam"], right_on=["season", "team"], how="left")
        .with_columns((pl.col("epa") - pl.col("def_epa_adj").fill_null(0.0)).alias("epa_adj"))
        .drop("def_epa_adj")
    )


def summarize(plays: pl.DataFrame, epa_col: str = "epa_adj") -> dict[str, float]:
    """Point estimates for one slice of dropbacks."""
    on = plays.filter(~pl.col("off_script"))[epa_col]
    off = plays.filter(pl.col("off_script"))[epa_col]
    return {
        "dropbacks": plays.height,
        "off_rate": off.len() / plays.height if plays.height else float("nan"),
        "epa_on": on.mean() if on.len() else float("nan"),
        "epa_off": off.mean() if off.len() else float("nan"),
        "gap": (off.mean() - on.mean()) if on.len() and off.len() else float("nan"),
    }


def bootstrap(plays: pl.DataFrame, epa_col: str = "epa_adj", n_boot: int = N_BOOT, seed: int = 0) -> dict[str, np.ndarray]:
    """Game-clustered bootstrap draws of each summarize() stat."""
    rng = np.random.default_rng(seed)
    games = plays.partition_by("game_id")
    # per-game sufficient stats: n, n_off, sum_epa_on, sum_epa_off
    stats = np.array([
        [
            g.height,
            g["off_script"].sum(),
            g.filter(~pl.col("off_script"))[epa_col].sum(),
            g.filter(pl.col("off_script"))[epa_col].sum(),
        ]
        for g in games
    ], dtype=float)
    idx = rng.integers(0, len(games), size=(n_boot, len(games)))
    n, n_off, s_on, s_off = (stats[idx, k].sum(axis=1) for k in range(4))
    with np.errstate(invalid="ignore", divide="ignore"):
        epa_on = s_on / (n - n_off)
        epa_off = s_off / n_off
        return {"off_rate": n_off / n, "epa_on": epa_on, "epa_off": epa_off, "gap": epa_off - epa_on}


def interval(draws: np.ndarray, level: float = 0.9) -> tuple[float, float]:
    lo = (1 - level) / 2
    return tuple(np.nanquantile(draws, [lo, 1 - lo]))


def qb_seasons(plays: pl.DataFrame, current_season: int = BRADY_START) -> pl.DataFrame:
    """League table: one row per QB-season, the distribution Allen sits in."""
    return (
        plays.group_by("season", "passer_id")
        .agg(
            pl.col("passer").mode().first(),
            pl.col("posteam").mode().first(),
            pl.len().alias("dropbacks"),
            pl.col("off_script").mean().alias("off_rate"),
            pl.col("epa_adj").filter(~pl.col("off_script")).mean().alias("epa_on"),
            pl.col("epa_adj").filter(pl.col("off_script")).mean().alias("epa_off"),
        )
        .with_columns((pl.col("epa_off") - pl.col("epa_on")).alias("gap"))
        .filter((pl.col("dropbacks") >= MIN_DROPBACKS) | (pl.col("season") == current_season))
        .with_columns(pl.col("off_rate").rank(descending=True).over("season").alias("off_rate_rank"))
        .sort("season", "off_rate", descending=[False, True])
    )


def era_shift(plays: pl.DataFrame, passer_id: str = ALLEN_ID, split: int = BRADY_START) -> pl.DataFrame:
    """Before vs after `split` for one QB, with 90% intervals on each era and
    on the change. This is the Q3 headline table."""
    qb = plays.filter(pl.col("passer_id") == passer_id)
    before, after = qb.filter(pl.col("season") < split), qb.filter(pl.col("season") >= split)
    b_draws, a_draws = bootstrap(before, seed=1), bootstrap(after, seed=2)
    b_pt, a_pt = summarize(before), summarize(after)

    rows = []
    for stat in ("off_rate", "epa_on", "epa_off", "gap"):
        b_lo, b_hi = interval(b_draws[stat])
        a_lo, a_hi = interval(a_draws[stat])
        d_lo, d_hi = interval(a_draws[stat] - b_draws[stat])
        rows.append({
            "stat": stat,
            "before": b_pt[stat], "before_lo": b_lo, "before_hi": b_hi,
            "after": a_pt[stat], "after_lo": a_lo, "after_hi": a_hi,
            "change": a_pt[stat] - b_pt[stat], "change_lo": d_lo, "change_hi": d_hi,
        })
    return pl.DataFrame(rows).with_columns(
        pl.lit(before.height).alias("n_before"), pl.lit(after.height).alias("n_after")
    )


def _check_bootstrap() -> None:
    # 10 games x 10 plays, exactly 3 off-script per game: every draw has off_rate 0.3
    fake = pl.DataFrame({
        "game_id": [g for g in range(10) for _ in range(10)],
        "off_script": [i < 3 for _ in range(10) for i in range(10)],
        "epa_adj": [1.0 if i < 3 else 0.0 for _ in range(10) for i in range(10)],
    })
    d = bootstrap(fake, n_boot=200)
    assert np.allclose(d["off_rate"], 0.3) and np.allclose(d["gap"], 1.0), d
    assert summarize(fake)["gap"] == 1.0


def _demo() -> None:
    _check_bootstrap()
    con = duckdb.connect(str(DB), read_only=True)
    try:
        plays = load_dropbacks(con)
    finally:
        con.close()
    assert plays.height > 0, "no dropbacks -- run refresh.py first"

    with pl.Config(tbl_rows=40, tbl_cols=-1, float_precision=3):
        print("=== Allen: 2022-2025 vs Brady era, 90% game-clustered intervals, opp-adjusted EPA ===")
        print(era_shift(plays))
        print("\n=== League off-script rate, QB-seasons (>= %d dropbacks, all 2026) ===" % MIN_DROPBACKS)
        print(qb_seasons(plays).filter(pl.col("passer_id") == ALLEN_ID))
        print(qb_seasons(plays).group_by("season").agg(
            pl.len().alias("qbs"),
            pl.col("off_rate").quantile(0.1).alias("p10"),
            pl.col("off_rate").median().alias("median"),
            pl.col("off_rate").quantile(0.9).alias("p90"),
        ).sort("season"))


if __name__ == "__main__":
    _demo()
