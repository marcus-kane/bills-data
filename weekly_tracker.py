"""weekly_tracker.py — regenerate every weekly table the post draws on.

Run after refresh.py, after every Bills game. Rebuilds each table in
data/derived/ from scratch off the current DuckDB (cheap, and avoids
append-log drift) and prints the headline rows.

    python refresh.py && python weekly_tracker.py

Writes:
    brady_fourth_down_tracker.csv  every Brady-era 4th down, running totals
    fourth_down_eras.csv           McDermott vs Brady, incl. Q2's go-rate on go-calls
    allen_off_script_eras.csv      Allen by play-caller era (Q3)
    team_ratings_<season>.csv      opponent-adjusted ratings + rank intervals (Q4)
    bills_defense_rank_change.csv  Bills defense rank vs the prior season (Q4 as logged)
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import polars as pl

sys.path.insert(0, str(Path(__file__).parent / "src"))
from fourth_down import BRADY_START, DB, bills_era_summary, brady_tracker, load_decisions  # noqa: E402
from off_script import era_table, load_dropbacks  # noqa: E402
from opponent_adjustment import rank_change, rating_intervals  # noqa: E402

OUT = Path("data/derived")
SEASON = BRADY_START


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        decisions = load_decisions(con, team="BUF")
        eras = era_table(load_dropbacks(con))
        ratings = rating_intervals(con, SEASON)
        defense = pl.DataFrame([rank_change(con, "BUF", "def", SEASON - 1, SEASON)])
    finally:
        con.close()

    tables = {
        "brady_fourth_down_tracker.csv": brady_tracker(decisions),
        "fourth_down_eras.csv": bills_era_summary(decisions),
        "allen_off_script_eras.csv": eras,
        f"team_ratings_{SEASON}.csv": ratings,
        "bills_defense_rank_change.csv": defense,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.write_csv(OUT / name)

    with pl.Config(tbl_rows=-1, tbl_cols=-1, float_precision=3, tbl_width_chars=200):
        print("=== Q2: Bills 4th downs by era ===")
        print(tables["fourth_down_eras.csv"])
        print("\n=== Q3: Allen by play-caller era ===")
        print(eras)
        print(f"\n=== Q4: Bills {SEASON} ratings (90% intervals; def rank 1 = best) ===")
        print(ratings.filter(pl.col("team") == "BUF"))
        print(f"\n=== Q4 as logged: Bills defense rank, {SEASON - 1} -> {SEASON} (negative = better) ===")
        print(defense)

    print()
    for name, df in tables.items():
        print(f"{df.height:>5} rows -> {OUT / name}")


if __name__ == "__main__":
    main()
