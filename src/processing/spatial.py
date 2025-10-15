from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import folium
from shapely.geometry import Point, box

from src.utils.io import ensure_directory


@dataclass(frozen=True)
class GridConfig:
    bbox: tuple[float, float, float, float]
    cell_size_deg: float = 0.02  # ~2km at equator; adjust per need


@dataclass(frozen=True)
class HeatmapConfig:
    parameter: str = "pm25"
    agg: str = "mean"  # mean/median/max


def dataframe_to_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(
        df.copy(),
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    return gdf


def make_grid(cfg: GridConfig) -> gpd.GeoDataFrame:
    min_lon, min_lat, max_lon, max_lat = cfg.bbox
    lon_vals = np.arange(min_lon, max_lon, cfg.cell_size_deg)
    lat_vals = np.arange(min_lat, max_lat, cfg.cell_size_deg)
    cells = []
    for lon in lon_vals:
        for lat in lat_vals:
            cells.append({
                "cell_lon": lon,
                "cell_lat": lat,
                "geometry": box(lon, lat, lon + cfg.cell_size_deg, lat + cfg.cell_size_deg)
            })
    grid = gpd.GeoDataFrame(cells, crs="EPSG:4326")
    return grid


def aggregate_to_grid(points: pd.DataFrame, grid: gpd.GeoDataFrame, parameter: str, agg: str = "mean") -> gpd.GeoDataFrame:
    pts = points[points["parameter"] == parameter]
    if pts.empty:
        grid = grid.copy()
        grid["value"] = np.nan
        grid["count"] = 0
        return grid

    gdf_points = dataframe_to_gdf(pts)
    # Spatial join points to grid cells
    joined = gpd.sjoin(gdf_points, grid, how="left", predicate="within")
    # Aggregate per grid cell polygon (by index_right)
    if agg == "mean":
        agg_func = "mean"
    elif agg == "median":
        agg_func = "median"
    elif agg == "max":
        agg_func = "max"
    else:
        raise ValueError(f"Unsupported agg: {agg}")

    grouped = joined.groupby("index_right")["value"].agg([agg_func, "count"]).reset_index()
    grouped = grouped.rename(columns={agg_func: "value"})

    result = grid.copy()
    result["index_right"] = result.index
    result = result.merge(grouped, on="index_right", how="left").drop(columns=["index_right"]).fillna({"value": np.nan, "count": 0})
    result["count"] = result["count"].astype(int)
    return result


def plot_static_heatmap(grid_stats: gpd.GeoDataFrame, output_png: str, cmap: str = "RdYlGn_r") -> None:
    ensure_directory(Path(output_png).parent)
    ax = grid_stats.plot(column="value", cmap=cmap, legend=True, figsize=(8, 8), edgecolor="none")
    ax.set_title("Pollutant concentration (grid-based)")
    ax.set_axis_off()
    fig = ax.get_figure()
    fig.savefig(output_png, dpi=150, bbox_inches="tight")


def make_folium_map(grid_stats: gpd.GeoDataFrame, output_html: str) -> None:
    ensure_directory(Path(output_html).parent)
    # Compute map center
    bounds = grid_stats.total_bounds  # minx, miny, maxx, maxy
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=grid_stats.to_json(),
        data=grid_stats,
        columns=[grid_stats.index, "value"],
        key_on="feature.id",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.0,
        nan_fill_opacity=0.1,
        legend_name="Concentration",
    ).add_to(m)

    m.save(output_html)
