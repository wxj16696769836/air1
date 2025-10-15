from __future__ import annotations

from typing import List

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def to_geodf(df: pd.DataFrame, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """Convert tabular measurements to GeoDataFrame with Point geometry."""
    geometry = [Point(lon, lat) for lat, lon in zip(df["latitude"], df["longitude"])]
    gdf = gpd.GeoDataFrame(df.copy(), geometry=geometry, crs=crs)
    return gdf


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-derived columns like date, hour, weekday, month, season, day_night."""
    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], utc=True, errors="coerce")
    out = out.dropna(subset=["datetime"]).reset_index(drop=True)
    out["date"] = out["datetime"].dt.date
    out["hour"] = out["datetime"].dt.hour
    out["weekday"] = out["datetime"].dt.weekday
    out["month"] = out["datetime"].dt.month

    def season_of_month(m: int) -> str:
        # Northern hemisphere
        if m in (12, 1, 2):
            return "winter"
        if m in (3, 4, 5):
            return "spring"
        if m in (6, 7, 8):
            return "summer"
        return "autumn"

    out["season"] = out["month"].apply(season_of_month)
    out["day_night"] = out["hour"].apply(lambda h: "day" if 7 <= h <= 18 else "night")
    return out
