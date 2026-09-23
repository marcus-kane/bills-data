"""Hourly weather per game, interpolated to each play. Infrastructure for Q1.

pbp carries one weather reading per game, often missing, from the nearest
airport. This pulls hourly METAR/ISD-Lite from the stations around the
stadium via meteostat, blends them by inverse distance, and linearly
interpolates to each play's wall-clock time -- 3-4 readings per game
instead of one.

Two things the blend does on purpose:
  - Direction is blended as u/v vectors, not degrees. Averaging 350 and 10
    as numbers gives 180 -- exactly backwards.
  - Wind speed stays in km/h (meteostat native). Convert at display time.

What this can't know: field-level wind. Every station is ~18 km away and
none of them sit inside a bowl. That gap is the whole point of Q1 -- the
architects claim the new bowl cuts field-level wind 50-67%, and this gives
the wind *above* the bowl to test that against.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import duckdb
import meteostat as ms
import numpy as np
import pandas as pd
import polars as pl

DB = Path("data/db/bills.duckdb")
RAW = Path("data/raw")

# stadium_id -> (lat, lon, elevation_m, IANA tz). New and old Highmark share
# BUF00 and sit across the road from each other -- same weather point.
# ponytail: Buffalo only. Q1 fits on every outdoor stadium 2016-2025; add
# their coordinates here before the fit, the pull already keys on stadium_id.
STADIUMS = {
    "BUF00": (42.774, -78.787, 200, "America/New_York"),
}

# Field axis bearing in degrees, per era. Calibration knob: CLAUDE.md says
# "roughly north-south" -- measure both fields off satellite imagery before
# anything gets published. Old and new Highmark are not guaranteed to match.
FIELD_AZIMUTH_DEG = {"old": 0.0, "new": 0.0}
NEW_HIGHMARK_SEASON = 2026

N_STATIONS = 4
PAD = timedelta(hours=1)          # pull an hour either side of the game
GAME_LENGTH = timedelta(hours=4)  # generous; OT games still fit


def _uv(speed: np.ndarray, from_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rad = np.deg2rad(from_deg)
    return -speed * np.sin(rad), -speed * np.cos(rad)


def fetch_game_hourly(lat: float, lon: float, elev: int, start_utc: pd.Timestamp, end_utc: pd.Timestamp) -> pd.DataFrame:
    """Hourly wind at a point: IDW blend of the nearest stations, as u/v."""
    point = ms.Point(lat, lon, elev)
    near = ms.stations.nearby(point, limit=N_STATIONS)
    raw = ms.hourly(near, start_utc.tz_localize(None).to_pydatetime(), end_utc.tz_localize(None).to_pydatetime()).fetch()
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["time", "u_kmh", "v_kmh", "wpgt_kmh", "n_stations"])

    df = raw.reset_index()[["station", "time", "wspd", "wdir", "wpgt"]].dropna(subset=["wspd", "wdir"])
    df["w"] = 1.0 / df["station"].map(near["distance"]).astype(float) ** 2
    df["u"], df["v"] = _uv(df["wspd"].to_numpy(float), df["wdir"].to_numpy(float))
    df["wu"], df["wv"] = df["u"] * df["w"], df["v"] * df["w"]

    g = df.groupby("time")
    out = pd.DataFrame(
        {
            "u_kmh": g["wu"].sum() / g["w"].sum(),
            "v_kmh": g["wv"].sum() / g["w"].sum(),
            "wpgt_kmh": g["wpgt"].max(),   # gusts: worst station, not the average
            "n_stations": g["station"].nunique(),
        }
    ).reset_index()
    out["time"] = pd.to_datetime(out["time"]).dt.tz_localize("UTC")
    return out


def fetch_season(season: int) -> pd.DataFrame:
    """Hourly wind for every completed outdoor game at a stadium in STADIUMS.

    Reads the season's schedule parquet, so refresh.py must pull schedules
    first (it does -- SOURCES is ordered).
    """
    sched = pd.read_parquet(RAW / "schedules" / f"{season}.parquet")
    games = sched[
        sched["stadium_id"].isin(STADIUMS.keys())
        & (sched["roof"] == "outdoors")
        & sched["result"].notna()
    ]
    frames = []
    for g in games.itertuples():
        lat, lon, elev, tz = STADIUMS[g.stadium_id]
        kickoff = pd.Timestamp(f"{g.gameday} {g.gametime}").tz_localize(tz).tz_convert("UTC")
        hourly = fetch_game_hourly(lat, lon, elev, kickoff - PAD, kickoff + GAME_LENGTH + PAD)
        hourly.insert(0, "game_id", g.game_id)
        hourly.insert(1, "stadium_id", g.stadium_id)
        frames.append(hourly)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def play_wind(con: duckdb.DuckDBPyConnection, season: int | None = None) -> pl.DataFrame:
    """Wind at each play's snap, linearly interpolated between hourly readings.

    along_kmh / cross_kmh are magnitudes relative to the field axis. They are
    unsigned on purpose: pbp doesn't say which end zone the offense is
    attacking, so head vs tail wind isn't knowable from public data.
    """
    plays = con.execute(
        f"""
        SELECT p.game_id, p.play_id, p.season, p.time_of_day
        FROM pbp p
        WHERE p.game_id IN (SELECT DISTINCT game_id FROM weather)
          AND p.time_of_day IS NOT NULL
          {"AND p.season = ?" if season else ""}
        """,
        [season] if season else [],
    ).df()
    weather = con.execute("SELECT * FROM weather ORDER BY game_id, time").df()

    plays["t"] = pd.to_datetime(plays["time_of_day"], utc=True, format="ISO8601").dt.as_unit("s").astype("int64")
    weather["t"] = pd.to_datetime(weather["time"], utc=True).dt.as_unit("s").astype("int64")

    parts = []
    for game_id, gp in plays.groupby("game_id"):
        gw = weather[weather["game_id"] == game_id]
        if gw.empty:
            continue
        gp = gp.copy()
        for col in ("u_kmh", "v_kmh"):
            gp[col] = np.interp(gp["t"], gw["t"], gw[col])  # clamps at the ends -- PAD keeps plays inside
        parts.append(gp)
    df = pd.concat(parts, ignore_index=True)

    df["wspd_kmh"] = np.hypot(df["u_kmh"], df["v_kmh"])
    df["wdir_from"] = (np.rad2deg(np.arctan2(-df["u_kmh"], -df["v_kmh"])) + 360) % 360
    azimuth = np.where(df["season"] >= NEW_HIGHMARK_SEASON, FIELD_AZIMUTH_DEG["new"], FIELD_AZIMUTH_DEG["old"])
    rel = np.deg2rad(df["wdir_from"] - azimuth)
    df["along_kmh"] = np.abs(df["wspd_kmh"] * np.cos(rel))
    df["cross_kmh"] = np.abs(df["wspd_kmh"] * np.sin(rel))

    return pl.from_pandas(
        df[["game_id", "play_id", "season", "wspd_kmh", "wdir_from", "along_kmh", "cross_kmh"]]
    )


def _demo() -> None:
    # vector blend: a north wind and a slightly-west-of-north wind must stay north
    u, v = _uv(np.array([10.0, 10.0]), np.array([10.0, 350.0]))
    back = (np.rad2deg(np.arctan2(-u.mean(), -v.mean())) + 360) % 360
    assert min(back, 360 - back) < 1e-6, back

    con = duckdb.connect(str(DB), read_only=True)
    try:
        wind = play_wind(con)
    finally:
        con.close()
    assert wind.height > 0, "no plays matched -- run refresh.py --full first"
    print(wind.group_by("game_id").agg(
        pl.len().alias("plays"),
        pl.col("wspd_kmh").min().round(1).alias("min_kmh"),
        pl.col("wspd_kmh").max().round(1).alias("max_kmh"),
    ).sort("game_id").tail(10))


if __name__ == "__main__":
    _demo()
