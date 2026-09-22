"""
refresh.py — re-pull only the current season and rebuild the DuckDB file.

This is the difference between a project and a notebook. Run it after every
Bills game (and any Tuesday once nflverse has finished the nightly update).

    python refresh.py              # current season only
    python refresh.py --full       # rebuild history from scratch
"""

from __future__ import annotations

import argparse
from pathlib import Path

CURRENT_SEASON = 2026
HISTORY_START = 2016      # pbp / NGS / participation floor
FTN_START = 2022          # FTN charting floor

RAW = Path("data/raw")
DB = Path("data/db/bills.duckdb")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full", action="store_true",
                   help="rebuild all seasons instead of just the current one")
    return p.parse_args()


def seasons(full: bool) -> list[int]:
    return list(range(HISTORY_START, CURRENT_SEASON + 1)) if full else [CURRENT_SEASON]


def pull(full: bool) -> None:
    """Land each source as parquet under data/raw/<source>/<season>.parquet."""
    raise NotImplementedError("Phase 0: wire up nfl_data_py pulls here")


def build_db() -> None:
    """Load every parquet in data/raw into a single DuckDB file."""
    raise NotImplementedError("Phase 0: wire up the DuckDB load here")


def main() -> None:
    args = parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    pull(args.full)
    build_db()


if __name__ == "__main__":
    main()
