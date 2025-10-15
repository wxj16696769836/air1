from __future__ import annotations

import argparse
from pathlib import Path
import os

import geopandas as gpd
import pandas as pd
from loguru import logger

from .alerts import generate_alerts
from .config import FetchConfig, Paths, Thresholds
from .fetch import fetch_openaq
from .preprocess import add_time_features, to_geodf
from .visualize import folium_heatmap
from .trends import plot_temporal_trends


def main() -> None:
    parser = argparse.ArgumentParser(description="Air quality spatiotemporal analysis")
    parser.add_argument("--city", type=str, default=None)
    parser.add_argument("--country", type=str, default=None)
    parser.add_argument("--bbox", type=float, nargs=4, default=None, help="minLon minLat maxLon maxLat")
    parser.add_argument("--start", type=str, default=None)
    parser.add_argument("--end", type=str, default=None)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--parameters", type=str, nargs="+", default=["pm25", "so2", "no2"])
    parser.add_argument("--api_key", type=str, default=None, help="OpenAQ v3 API key or set OPENAQ_API_KEY env")
    parser.add_argument("--csv", type=str, default=None, help="Path to local CSV with columns latitude,longitude,parameter,value,datetime")
    parser.add_argument("--pm25_thr", type=float, default=150.0)
    parser.add_argument("--so2_thr", type=float, default=350.0)
    parser.add_argument("--no2_thr", type=float, default=200.0)
    parser.add_argument("--out_prefix", type=str, default="outputs/aq_analysis")
    parser.add_argument("--max_pages", type=int, default=5)

    args = parser.parse_args()

    paths = Paths()
    Path(paths.data_dir).mkdir(parents=True, exist_ok=True)
    Path(paths.outputs_dir).mkdir(parents=True, exist_ok=True)
    Path(paths.maps_dir).mkdir(parents=True, exist_ok=True)
    Path(paths.plots_dir).mkdir(parents=True, exist_ok=True)
    Path(paths.alerts_dir).mkdir(parents=True, exist_ok=True)

    # Data acquisition: CSV takes priority, else OpenAQ
    if args.csv:
        df = pd.read_csv(args.csv)
        logger.info(f"Loaded {len(df)} rows from CSV {args.csv}")
    else:
        api_key = args.api_key or os.environ.get("OPENAQ_API_KEY")
        cfg = FetchConfig(
            city=args.city,
            country=args.country,
            bbox=args.bbox,
            start=args.start,
            end=args.end,
            parameters=args.parameters,
            limit=args.limit,
            api_key=api_key,
        )
        df = fetch_openaq(cfg, max_pages=args.max_pages)
        if df.empty:
            logger.warning("No data fetched. Consider providing --api_key for v3, a broader query, or --csv.")
            return

    df = add_time_features(df)
    gdf = to_geodf(df)

    # Save raw preprocessed data
    raw_csv = f"{args.out_prefix}_data.csv"
    df.to_csv(raw_csv, index=False)
    logger.info(f"Saved data to {raw_csv}")

    # Heatmap for PM2.5
    m = folium_heatmap(gdf, parameter="pm25")
    heatmap_html = f"{paths.maps_dir}/pm25_heatmap.html"
    m.save(heatmap_html)
    logger.info(f"Saved heatmap to {heatmap_html}")

    # Alerts
    thr = {"pm25": args.pm25_thr, "so2": args.so2_thr, "no2": args.no2_thr}
    alerts_df = generate_alerts(df, thr)
    alerts_csv = f"{paths.alerts_dir}/alerts.csv"
    alerts_df.to_csv(alerts_csv, index=False)
    logger.info(f"Saved alerts to {alerts_csv} with {len(alerts_df)} rows")

    # Temporal trends
    trends_png = f"{paths.plots_dir}/trends.png"
    plot_temporal_trends(df, trends_png)
    logger.info(f"Saved temporal trend plots to {trends_png.replace('.png', '_*.png')}")


if __name__ == "__main__":
    main()
