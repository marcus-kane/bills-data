"""Opponent-adjusted EPA: infrastructure for Q1-Q3, and the answer to Q4.

Q4: is Leonhard's defense actually better, or is the schedule easier? A
team's raw EPA/play conflates "how good are they" with "who did they play."
This fits a ridge regression per play: epa ~ offense_team + defense_team,
which separates the two into an offense rating and a defense rating per
team, each shrunk toward the league-mean prior (0) by the ridge penalty --
exactly what's needed early in a season when a team's own record is still
mostly noise.

Two judgment calls, documented rather than hidden:
  - Garbage time is filtered by win probability in [0.05, 0.95]. Standard
    cutoff, not the only defensible one.
  - Playoffs are excluded (REG season only) so ratings don't mix seeding
    incentives into the model.

No ground truth exists to validate an "adjusted EPA" rating against, so the
only honest test is out-of-sample: fit ratings on weeks before week N, and
see whether they predict week N's actual offensive output better than a
team's own unadjusted trailing average does. See validate().
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import polars as pl
from sklearn.linear_model import Ridge

DB = Path("data/db/bills.duckdb")

WP_LOW, WP_HIGH = 0.05, 0.95  # garbage-time filter


def load_plays(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Regular-season rush/pass plays outside garbage time, one row per play."""
    query = """
        SELECT season, week, posteam, defteam, epa
        FROM pbp
        WHERE season_type = 'REG'
          AND (rush_attempt = 1 OR pass_attempt = 1)
          AND epa IS NOT NULL
          AND posteam IS NOT NULL AND defteam IS NOT NULL
          AND wp BETWEEN ? AND ?
    """
    return pl.from_arrow(con.execute(query, [WP_LOW, WP_HIGH]).arrow())


def fit_ratings(train: pd.DataFrame, alpha: float) -> tuple[dict[str, float], dict[str, float], float]:
    """Ridge-fit offense/defense team ratings on a slice of plays.

    epa ~ intercept + off_rating[posteam] + def_rating[defteam], L2-penalized
    so a team with few plays in `train` gets pulled toward 0 (league average).
    """
    off = pd.get_dummies(train["posteam"], prefix="off")
    defn = pd.get_dummies(train["defteam"], prefix="def")
    X = pd.concat([off, defn], axis=1)
    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X, train["epa"])

    off_ratings = {c.removeprefix("off_"): coef for c, coef in zip(off.columns, model.coef_[: off.shape[1]])}
    def_ratings = {c.removeprefix("def_"): coef for c, coef in zip(defn.columns, model.coef_[off.shape[1]:])}
    return off_ratings, def_ratings, float(model.intercept_)


def current_ratings(con: duckdb.DuckDBPyConnection, season: int, alpha: float = 30.0) -> pl.DataFrame:
    """Offense/defense ratings fit on every play of `season` so far."""
    plays = load_plays(con).filter(pl.col("season") == season).to_pandas()
    off_ratings, def_ratings, intercept = fit_ratings(plays, alpha)
    teams = sorted(set(off_ratings) | set(def_ratings))
    return pl.DataFrame(
        {
            "team": teams,
            "off_epa_adj": [off_ratings.get(t, 0.0) for t in teams],
            "def_epa_adj": [def_ratings.get(t, 0.0) for t in teams],
        }
    ).with_columns((pl.col("off_epa_adj") - pl.col("def_epa_adj")).alias("net_epa_adj")).sort(
        "net_epa_adj", descending=True
    )


def walk_forward(plays: pl.DataFrame, alpha: float, min_prior_weeks: int = 1) -> pl.DataFrame:
    """For every (season, week) with at least `min_prior_weeks` of that
    season already played, fit ratings on the prior weeks only and predict
    each team's average offensive EPA/play in the coming week two ways:
    raw (team's own trailing average, ignoring the opponent) and adjusted
    (ridge off/def ratings). Returns one row per team-week actually played.
    """
    plays_pd = plays.to_pandas()
    rows = []
    for season, season_df in plays_pd.groupby("season"):
        weeks = sorted(season_df["week"].unique())
        for week in weeks:
            train = season_df[season_df["week"] < week]
            test = season_df[season_df["week"] == week]
            if train.empty or train["week"].nunique() < min_prior_weeks:
                continue

            off_ratings, def_ratings, intercept = fit_ratings(train, alpha)
            league_mean = train["epa"].mean()
            raw_off = train.groupby("posteam")["epa"].mean().to_dict()

            for (posteam, defteam), grp in test.groupby(["posteam", "defteam"]):
                rows.append(
                    {
                        "season": season,
                        "week": week,
                        "posteam": posteam,
                        "defteam": defteam,
                        "n_plays": len(grp),
                        "actual_epa": grp["epa"].mean(),
                        "raw_pred_epa": raw_off.get(posteam, league_mean),
                        "adj_pred_epa": intercept + off_ratings.get(posteam, 0.0) + def_ratings.get(defteam, 0.0),
                    }
                )
    return pl.DataFrame(rows)


def validate(walk_df: pl.DataFrame) -> dict[str, float]:
    """Out-of-sample MAE, raw vs adjusted, weighted by plays per team-game."""
    w = walk_df["n_plays"].to_numpy()
    actual = walk_df["actual_epa"].to_numpy()
    raw_mae = float(np.average(np.abs(actual - walk_df["raw_pred_epa"].to_numpy()), weights=w))
    adj_mae = float(np.average(np.abs(actual - walk_df["adj_pred_epa"].to_numpy()), weights=w))
    return {
        "raw_mae": raw_mae,
        "adjusted_mae": adj_mae,
        "improvement_pct": (raw_mae - adj_mae) / raw_mae * 100,
    }


def _demo() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        plays = load_plays(con)
    finally:
        con.close()

    assert plays.height > 0, "no plays loaded -- check the wp / season_type filters"

    print("=== alpha sweep, out-of-sample MAE (lower is better) ===")
    best_alpha, best_result = None, None
    for alpha in (1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0):
        walk = walk_forward(plays, alpha=alpha)
        result = validate(walk)
        print(f"  alpha={alpha:>6.0f}  raw_mae={result['raw_mae']:.4f}  "
              f"adjusted_mae={result['adjusted_mae']:.4f}  "
              f"improvement={result['improvement_pct']:+.1f}%")
        if best_result is None or result["adjusted_mae"] < best_result["adjusted_mae"]:
            best_alpha, best_result = alpha, result

    print(f"\nbest alpha: {best_alpha} ({best_result['improvement_pct']:+.1f}% vs raw)")

    con = duckdb.connect(str(DB), read_only=True)
    try:
        ratings = current_ratings(con, season=2026, alpha=best_alpha)
    finally:
        con.close()
    print("\n=== 2026 season-to-date ratings (net_epa_adj = off - def, higher is better) ===")
    with pl.Config(tbl_rows=32):
        print(ratings)


if __name__ == "__main__":
    _demo()
