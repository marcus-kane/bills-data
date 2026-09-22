"""
refresh.py — re-pull only the current season and rebuild the DuckDB file.

This is the difference between a project and a notebook. Run it after every
Bills game (and any Tuesday once nflverse has finished the nightly update).

    python refresh.py              # current season only
    python refresh.py --full       # rebuild history from scratch
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import duckdb
import nfl_data_py as nfl
import pandas as pd

CURRENT_SEASON = 2026
HISTORY_START = 2016      # pbp / NGS / participation floor
FTN_START = 2022          # FTN charting floor
PFR_START = 2018          # PFR advanced weekly floor

RAW = Path("data/raw")
DB = Path("data/db/bills.duckdb")


def _fetch_ngs(season: int) -> pd.DataFrame:
    frames = []
    for stat_type in ("passing", "rushing", "receiving"):
        df = nfl.import_ngs_data(stat_type, [season])
        df["stat_type"] = stat_type
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _fetch_pfr_advanced(season: int) -> pd.DataFrame:
    frames = []
    for stat_type in ("pass", "rec", "rush"):
        df = nfl.import_weekly_pfr(stat_type, [season])
        df["stat_type"] = stat_type
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# source name -> (earliest season available, fetch(season) -> DataFrame)
SOURCES = {
    "pbp": (HISTORY_START, lambda season: nfl.import_pbp_data([season], downcast=True)),
    "ftn": (FTN_START, lambda season: nfl.import_ftn_data([season])),
    "ngs_weekly": (HISTORY_START, _fetch_ngs),
    "snap_counts": (HISTORY_START, lambda season: nfl.import_snap_counts([season])),
    "pfr_advanced_weekly": (PFR_START, _fetch_pfr_advanced),
    "schedules": (HISTORY_START, lambda season: nfl.import_schedules([season])),
    "injuries": (HISTORY_START, lambda season: nfl.import_injuries([season])),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full", action="store_true",
                   help="rebuild all seasons instead of just the current one")
    return p.parse_args()


def seasons(full: bool) -> list[int]:
    return list(range(HISTORY_START, CURRENT_SEASON + 1)) if full else [CURRENT_SEASON]


def pull(full: bool) -> None:
    """Land each source as parquet under data/raw/<source>/<season>.parquet."""
    warnings.filterwarnings("ignore")  # nfl_data_py's pandas-version pin nags on every import
    for source, (floor, fetch) in SOURCES.items():
        for season in seasons(full):
            if season < floor:
                continue
            path = RAW / source / f"{season}.parquet"
            # the current season is always re-pulled -- that's the point of
            # this script. Older seasons are done once and cached.
            if season != CURRENT_SEASON and path.exists():
                print(f"  {source} {season}: cached, skipping")
                continue
            print(f"  {source} {season}: pulling...")
            df = fetch(season)
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
            print(f"  {source} {season}: {len(df)} rows")


def build_db() -> None:
    """Load every parquet in data/raw into a single DuckDB file, one table per source."""
    con = duckdb.connect(str(DB))
    try:
        for source_dir in sorted(p for p in RAW.iterdir() if p.is_dir()):
            if not any(source_dir.glob("*.parquet")):
                continue
            table = source_dir.name
            glob_path = (source_dir / "*.parquet").as_posix()
            con.execute(
                f"CREATE OR REPLACE TABLE {table} AS "
                f"SELECT * FROM read_parquet('{glob_path}', union_by_name=True)"
            )
            n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n} rows")
    finally:
        con.close()


def main() -> None:
    args = parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    pull(args.full)
    build_db()


if __name__ == "__main__":
    main()
