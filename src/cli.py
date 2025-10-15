from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
import pandas as pd

from src.data_collect.openaq import OpenAQQuery, fetch_measurements
from src.data_collect.demo import DemoConfig, generate_demo_measurements
from src.processing.spatial import GridConfig, HeatmapConfig, make_grid, aggregate_to_grid, plot_static_heatmap, make_folium_map
from src.processing.alerts import DEFAULT_THRESHOLDS, compute_alerts, save_alerts, summarize_alerts
from src.processing.temporal import TemporalConfig, daily_trend, hourly_profile, weekday_profile, monthly_profile
from src.utils.io import ensure_directory


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--city", type=str, default=None, help="City name for OpenAQ query")
@click.option("--country", type=str, default=None, help="Country code for OpenAQ query")
@click.option("--bbox", type=str, default=None, help="min_lon,min_lat,max_lon,max_lat")
@click.option("--start", type=str, default=None, help="ISO8601 start datetime (UTC)")
@click.option("--end", type=str, default=None, help="ISO8601 end datetime (UTC)")
@click.option("--output", type=click.Path(dir_okay=False), default="data/raw/openaq.csv")
@click.option("--max-pages", type=int, default=3)
@click.option("--params", type=str, default="pm25,so2,no2")
def fetch(city: str | None, country: str | None, bbox: str | None, start: str | None, end: str | None, output: str, max_pages: int, params: str) -> None:
    """Fetch measurements from OpenAQ into CSV."""
    bbox_tuple = None
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise click.BadParameter("bbox must be 'min_lon,min_lat,max_lon,max_lat'")
        bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

    parameters = tuple(p.strip().lower() for p in params.split(",") if p.strip())

    start_dt = pd.to_datetime(start, utc=True) if start else None
    end_dt = pd.to_datetime(end, utc=True) if end else None

    q = OpenAQQuery(parameters=parameters, city=city, country=country, bbox=bbox_tuple, start=start_dt, end=end_dt, max_pages=max_pages)
    df = fetch_measurements(q)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    click.echo(f"Saved {len(df)} rows to {output}")


@cli.command()
@click.option("--bbox", type=str, required=True, help="min_lon,min_lat,max_lon,max_lat")
@click.option("--hours", type=int, default=24)
@click.option("--points-per-hour", type=int, default=60)
@click.option("--output", type=click.Path(dir_okay=False), default="data/raw/demo.csv")
@click.option("--seed", type=int, default=42)
def gen_demo(bbox: str, hours: int, points_per_hour: int, output: str, seed: int) -> None:
    """Generate synthetic demo measurements within bbox for given hours."""
    parts = [float(x) for x in bbox.split(",")]
    if len(parts) != 4:
        raise click.BadParameter("bbox must be 'min_lon,min_lat,max_lon,max_lat'")
    bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(hours=hours)

    cfg = DemoConfig(bbox=bbox_tuple, start=start, end=end, points_per_hour=points_per_hour, seed=seed)
    df = generate_demo_measurements(cfg)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    click.echo(f"Saved {len(df)} demo rows to {output}")


@cli.command()
@click.option("--input", type=click.Path(exists=True, dir_okay=False), default="data/raw/demo.csv")
@click.option("--parameter", type=str, default="pm25")
@click.option("--cell-size", type=float, default=0.02)
@click.option("--png", type=click.Path(dir_okay=False), default="outputs/figures/heatmap.png")
@click.option("--html", type=click.Path(dir_okay=False), default="outputs/figures/heatmap.html")
@click.option("--agg", type=str, default="mean")
@click.option("--bbox", type=str, default=None, help="min_lon,min_lat,max_lon,max_lat (if omitted, infer from data)")
def heatmap(input: str, parameter: str, cell_size: float, png: str, html: str, agg: str, bbox: str | None) -> None:
    """Create grid-based heatmaps (static PNG and Folium HTML)."""
    df = pd.read_csv(input, parse_dates=["timestamp"])  # type: ignore[arg-type]
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise click.BadParameter("bbox must be 'min_lon,min_lat,max_lon,max_lat'")
        bbox_tuple = (parts[0], parts[1], parts[2], parts[3])
    else:
        # infer bounds with padding
        min_lon = df["longitude"].min(); max_lon = df["longitude"].max()
        min_lat = df["latitude"].min(); max_lat = df["latitude"].max()
        pad_lon = 0.01 * (max_lon - min_lon)
        pad_lat = 0.01 * (max_lat - min_lat)
        bbox_tuple = (min_lon - pad_lon, min_lat - pad_lat, max_lon + pad_lon, max_lat + pad_lat)

    grid_cfg = GridConfig(bbox=bbox_tuple, cell_size_deg=cell_size)
    grid = make_grid(grid_cfg)
    stats = aggregate_to_grid(df, grid, parameter=parameter, agg=agg)

    plot_static_heatmap(stats, png)
    make_folium_map(stats, html)
    click.echo(f"Saved heatmap to {png} and {html}")


@cli.command()
@click.option("--input", type=click.Path(exists=True, dir_okay=False), default="data/raw/demo.csv")
@click.option("--output", type=click.Path(dir_okay=False), default="outputs/alerts/alerts.csv")
def alerts(input: str, output: str) -> None:
    """Compute threshold-based alerts and export CSV."""
    df = pd.read_csv(input, parse_dates=["timestamp"])  # type: ignore[arg-type]
    alerts_df = compute_alerts(df)
    save_alerts(alerts_df, output)
    summary = summarize_alerts(alerts_df)
    click.echo(summary.to_string(index=False))
    click.echo(f"Saved {len(alerts_df)} alerts to {output}")


@cli.command()
@click.option("--input", type=click.Path(exists=True, dir_okay=False), default="data/raw/demo.csv")
@click.option("--parameter", type=str, default="pm25")
@click.option("--outdir", type=click.Path(file_okay=False), default="outputs/figures")
def temporal(input: str, parameter: str, outdir: str) -> None:
    """Generate temporal analysis plots (daily, hourly, weekday, monthly)."""
    df = pd.read_csv(input, parse_dates=["timestamp"])  # type: ignore[arg-type]
    ensure_directory(outdir)
    cfg = TemporalConfig(parameter=parameter)
    daily_trend(df, cfg, Path(outdir) / f"daily_{parameter}.png")
    hourly_profile(df, cfg, Path(outdir) / f"hourly_{parameter}.png")
    weekday_profile(df, cfg, Path(outdir) / f"weekday_{parameter}.png")
    monthly_profile(df, cfg, Path(outdir) / f"monthly_{parameter}.png")
    click.echo("Saved temporal plots.")


@cli.command()
@click.option("--bbox", type=str, default="116.2,39.7,116.6,40.1", help="Default bbox around Beijing area")
@click.option("--hours", type=int, default=48)
@click.option("--points-per-hour", type=int, default=80)
@click.option("--parameter", type=str, default="pm25")
@click.option("--cell-size", type=float, default=0.02)
@click.option("--agg", type=str, default="mean")
@click.option("--outdir", type=click.Path(file_okay=False), default="outputs")
@click.option("--seed", type=int, default=7)
def run_demo(bbox: str, hours: int, points_per_hour: int, parameter: str, cell_size: float, agg: str, outdir: str, seed: int) -> None:
    """Run full demo pipeline: generate data, heatmaps, alerts, temporal plots."""
    outdir_path = Path(outdir)
    raw_csv = Path("data/raw/demo.csv")

    # 1) Generate demo data
    parts = [float(x) for x in bbox.split(",")]
    bbox_tuple = (parts[0], parts[1], parts[2], parts[3])
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(hours=hours)
    demo_cfg = DemoConfig(bbox=bbox_tuple, start=start, end=end, points_per_hour=points_per_hour, seed=seed)
    df = generate_demo_measurements(demo_cfg)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_csv, index=False)

    # 2) Heatmaps
    figures_dir = outdir_path / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    grid_cfg = GridConfig(bbox=bbox_tuple, cell_size_deg=cell_size)
    grid = make_grid(grid_cfg)
    stats = aggregate_to_grid(df, grid, parameter=parameter, agg=agg)
    plot_static_heatmap(stats, str(figures_dir / "heatmap.png"))
    make_folium_map(stats, str(figures_dir / "heatmap.html"))

    # 3) Alerts
    alerts_csv = outdir_path / "alerts" / "alerts.csv"
    alerts_df = compute_alerts(df)
    alerts_csv.parent.mkdir(parents=True, exist_ok=True)
    alerts_df.to_csv(alerts_csv, index=False)

    # 4) Temporal
    temporal_cfg = TemporalConfig(parameter=parameter)
    daily_trend(df, temporal_cfg, figures_dir / f"daily_{parameter}.png")
    hourly_profile(df, temporal_cfg, figures_dir / f"hourly_{parameter}.png")
    weekday_profile(df, temporal_cfg, figures_dir / f"weekday_{parameter}.png")
    monthly_profile(df, temporal_cfg, figures_dir / f"monthly_{parameter}.png")

    click.echo("Demo pipeline completed.")


if __name__ == "__main__":
    cli()
