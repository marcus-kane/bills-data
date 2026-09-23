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
ALPHA = 300.0  # ridge penalty picked by the walk-forward sweep in _demo() (+7.5% MAE vs raw)
N_BOOT = 500
# Game-clustered bootstrap is degenerate with very few games: with 2 games
# there are only 3 distinct resamples, and a team whose games all drop out
# of a draw snaps to the prior (exactly 0). Below this, intervals are NaN
# rather than a number that looks trustworthy. Percentile intervals stay
# somewhat narrow until ~10 games; say so when citing early-season bands.
MIN_GAMES = 4


def load_plays(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Regular-season rush/pass plays outside garbage time, one row per play."""
    query = """
        SELECT season, week, game_id, posteam, defteam, epa
        FROM pbp
        WHERE season_type = 'REG'
          AND (rush_attempt = 1 OR pass_attempt = 1)
          AND epa IS NOT NULL
          AND posteam IS NOT NULL AND defteam IS NOT NULL
          AND wp BETWEEN ? AND ?
    """
    return pl.from_arrow(con.execute(query, [WP_LOW, WP_HIGH]).arrow())


def fit_ratings(
    train: pd.DataFrame, alpha: float, sample_weight: np.ndarray | None = None
) -> tuple[dict[str, float], dict[str, float], float]:
    """Ridge-fit offense/defense team ratings on a slice of plays.

    epa ~ intercept + off_rating[posteam] + def_rating[defteam], L2-penalized
    so a team with few plays in `train` gets pulled toward 0 (league average).
    `train` can also be pre-aggregated cells (mean epa, weight = play count):
    squared loss makes that exactly the same fit.
    """
    off = pd.get_dummies(train["posteam"], prefix="off")
    defn = pd.get_dummies(train["defteam"], prefix="def")
    X = pd.concat([off, defn], axis=1)
    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X, train["epa"], sample_weight=sample_weight)

    off_ratings = {c.removeprefix("off_"): coef for c, coef in zip(off.columns, model.coef_[: off.shape[1]])}
    def_ratings = {c.removeprefix("def_"): coef for c, coef in zip(defn.columns, model.coef_[off.shape[1]:])}
    return off_ratings, def_ratings, float(model.intercept_)


def current_ratings(con: duckdb.DuckDBPyConnection, season: int, alpha: float = ALPHA) -> pl.DataFrame:
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


def _cells(plays: pd.DataFrame) -> pd.DataFrame:
    """Collapse plays to one row per (game, offense, defense): mean epa + count.
    ~550 rows a season instead of ~30k, which is what makes 500 refits cheap."""
    return plays.groupby(["game_id", "posteam", "defteam"], as_index=False).agg(
        n=("epa", "size"), epa=("epa", "mean")
    )


def rating_draws(
    plays: pd.DataFrame, alpha: float = ALPHA, n_boot: int = N_BOOT, seed: int = 0
) -> tuple[list[str], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Point ratings plus game-clustered bootstrap draws.

    Resamples whole games with replacement (as multinomial weights, so no
    rows get copied) and refits. Plays within a game share a game plan and
    conditions, so resampling plays independently would understate the
    noise. Returns (teams, point, draws): point[kind] is (n_teams,),
    draws[kind] is (n_boot, n_teams), kind in off / def / net.
    """
    cells = _cells(plays)
    game_idx, games = pd.factorize(cells["game_id"])
    teams = sorted(set(cells["posteam"]) | set(cells["defteam"]))
    n = cells["n"].to_numpy(float)

    def fit(game_weight: np.ndarray) -> dict[str, np.ndarray]:
        off, dfn, _ = fit_ratings(cells, alpha, sample_weight=n * game_weight[game_idx])
        o = np.array([off.get(t, 0.0) for t in teams])
        d = np.array([dfn.get(t, 0.0) for t in teams])
        return {"off": o, "def": d, "net": o - d}

    point = fit(np.ones(len(games)))
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(len(games), np.full(len(games), 1 / len(games)), size=n_boot).astype(float)
    fits = [fit(c) for c in counts]
    draws = {k: np.vstack([f[k] for f in fits]) for k in point}
    return teams, point, draws


def _rank(x: np.ndarray, better_high: bool) -> np.ndarray:
    """1 = best, along the last axis."""
    return (-x if better_high else x).argsort(axis=-1).argsort(axis=-1) + 1


# off: EPA gained above average, higher is better. def: EPA allowed above
# average, lower is better. net = off - def, higher is better.
BETTER_HIGH = {"off": True, "def": False, "net": True}


def rating_intervals(
    con: duckdb.DuckDBPyConnection, season: int, alpha: float = ALPHA,
    n_boot: int = N_BOOT, level: float = 0.9,
) -> pl.DataFrame:
    """Season-to-date ratings and ranks, each with a `level` interval.

    Rank intervals are the honest version of a power ranking: early in a
    season most teams' rank bands cover half the league, and that's the
    point -- it says how far a rank can be trusted yet.
    """
    plays = load_plays(con).filter(pl.col("season") == season).to_pandas()
    teams, point, draws = rating_draws(plays, alpha, n_boot)
    games = np.array([_games(plays, t) for t in teams])
    enough = games >= MIN_GAMES
    q = [(1 - level) / 2, 1 - (1 - level) / 2]
    cols: dict[str, object] = {"season": [season] * len(teams), "team": teams, "games": games}
    for kind, high in BETTER_HIGH.items():
        lo, hi = np.quantile(draws[kind], q, axis=0)
        r_best, r_worst = np.quantile(_rank(draws[kind], high), q, axis=0, method="inverted_cdf")
        cols |= {
            f"{kind}_epa_adj": point[kind],
            f"{kind}_lo": np.where(enough, lo, np.nan), f"{kind}_hi": np.where(enough, hi, np.nan),
            f"{kind}_rank": _rank(point[kind], high),
            f"{kind}_rank_best": np.where(enough, r_best, np.nan),
            f"{kind}_rank_worst": np.where(enough, r_worst, np.nan),
        }
    return pl.DataFrame(cols).sort("net_rank")


def _games(plays: pd.DataFrame, team: str) -> int:
    return plays.loc[(plays["posteam"] == team) | (plays["defteam"] == team), "game_id"].nunique()


def rank_change(
    con: duckdb.DuckDBPyConnection, team: str, kind: str, season_from: int, season_to: int,
    alpha: float = ALPHA, n_boot: int = N_BOOT, level: float = 0.9,
) -> dict[str, int | None]:
    """Change in one team's rank between two seasons, with an interval
    (None until both seasons have MIN_GAMES).

    Negative change = moved up (better). The two seasons are bootstrapped
    independently, so the interval carries both seasons' noise. This scores
    Q4: Bills defense 2026 vs 2025.
    """
    all_plays = load_plays(con)
    out, rank_draws, min_games = {}, {}, []
    for label, season, seed in (("from", season_from, 1), ("to", season_to, 2)):
        plays = all_plays.filter(pl.col("season") == season).to_pandas()
        teams, point, draws = rating_draws(plays, alpha, n_boot, seed=seed)
        i = teams.index(team)
        out[f"rank_{label}"] = int(_rank(point[kind], BETTER_HIGH[kind])[i])
        out[f"games_{label}"] = _games(plays, team)
        rank_draws[label] = _rank(draws[kind], BETTER_HIGH[kind])[:, i]
    out["change"] = out["rank_to"] - out["rank_from"]
    if min(out["games_from"], out["games_to"]) < MIN_GAMES:
        return out | {"change_lo": None, "change_hi": None}
    lo, hi = np.quantile(rank_draws["to"] - rank_draws["from"], [(1 - level) / 2, 1 - (1 - level) / 2],
                         method="inverted_cdf")
    return out | {"change_lo": int(lo), "change_hi": int(hi)}


def _check_cells() -> None:
    """The cell-aggregated weighted fit must equal the play-level fit exactly."""
    rng = np.random.default_rng(0)
    teams = list("ABCD")
    rows = []
    for g in range(12):
        a, b = rng.choice(teams, 2, replace=False)
        for off, dfn in ((a, b), (b, a)):
            for _ in range(rng.integers(20, 40)):
                rows.append({"game_id": g, "posteam": off, "defteam": dfn,
                             "epa": rng.normal(0.1 * teams.index(off), 1)})
    plays = pd.DataFrame(rows)
    play_off, play_def, _ = fit_ratings(plays, 50.0)
    cells = _cells(plays)
    cell_off, cell_def, _ = fit_ratings(cells, 50.0, sample_weight=cells["n"].to_numpy(float))
    for t in teams:
        assert np.isclose(play_off[t], cell_off[t]) and np.isclose(play_def[t], cell_def[t]), t
    assert _rank(np.array([0.3, -0.1, 0.2]), better_high=True).tolist() == [1, 3, 2]
    assert _rank(np.array([0.3, -0.1, 0.2]), better_high=False).tolist() == [3, 1, 2]
    teams_out, _, draws = rating_draws(plays, 50.0, n_boot=50)
    assert draws["def"].shape == (50, len(teams_out))


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
    _check_cells()
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
        ratings = rating_intervals(con, season=2026, alpha=best_alpha)
    finally:
        con.close()
    print("\n=== 2026 season-to-date ratings + ranks, 90% game-clustered intervals ===")
    with pl.Config(tbl_rows=32, tbl_cols=-1):
        print(ratings)


if __name__ == "__main__":
    _demo()
