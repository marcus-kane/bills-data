"""weekly_tracker.py — regenerate the live Brady fourth-down tracker.

Run after refresh.py, after every Bills game. Rebuilds
data/derived/brady_fourth_down_tracker.csv from scratch off the current
DuckDB (it's cheap and avoids append-log drift) and prints it.

    python refresh.py && python weekly_tracker.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import polars as pl

sys.path.insert(0, str(Path(__file__).parent / "src"))
from fourth_down import DB, brady_tracker, load_decisions  # noqa: E402

OUT = Path("data/derived/brady_fourth_down_tracker.csv")


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        decisions = load_decisions(con, team="BUF")
    finally:
        con.close()

    tracker = brady_tracker(decisions)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tracker.write_csv(OUT)

    with pl.Config(tbl_rows=-1, tbl_cols=-1):
        print(tracker)
    print(f"\n{tracker.height} Brady-era 4th downs -> {OUT}")


if __name__ == "__main__":
    main()
