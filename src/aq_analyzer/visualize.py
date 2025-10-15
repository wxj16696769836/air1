from __future__ import annotations

from typing import Optional

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from folium.plugins import HeatMap


def folium_heatmap(
    gdf: gpd.GeoDataFrame,
    parameter: str = "pm25",
    min_opacity: float = 0.2,
    radius: int = 15,
    blur: int = 20,
    max_zoom: int = 12,
    tiles: str = "cartodbpositron",
) -> folium.Map:
    df = gdf[gdf["parameter"] == parameter]
    if df.empty:
        # create a default map centered at 0,0
        m = folium.Map(location=[0, 0], zoom_start=2, tiles=tiles)
        return m

    lat_center = df["latitude"].astype(float).mean()
    lon_center = df["longitude"].astype(float).mean()
    m = folium.Map(location=[lat_center, lon_center], zoom_start=10, tiles=tiles)

    heat_data = df[["latitude", "longitude", "value"]].dropna().values.tolist()
    HeatMap(
        heat_data,
        min_opacity=min_opacity,
        radius=radius,
        blur=blur,
        max_zoom=max_zoom,
    ).add_to(m)
    return m
