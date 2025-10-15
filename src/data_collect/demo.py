from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DemoConfig:
    bbox: tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    start: datetime
    end: datetime
    points_per_hour: int = 60
    seed: Optional[int] = 42


def _seasonal_multiplier(ts: pd.Timestamp) -> float:
    # Simple seasonal curve: higher in winter months
    month = ts.month
    # Peak in January (1.3), trough in July (0.7)
    seasonal = 1.0 + 0.3 * np.cos((month - 1) / 12 * 2 * np.pi)
    return float(seasonal)


def _diurnal_multiplier(ts: pd.Timestamp) -> float:
    # Morning/evening peaks typical for traffic-related pollutants
    hour = ts.hour
    diurnal = 1.0 + 0.25 * np.cos((hour - 8) / 24 * 2 * np.pi) + 0.2 * np.cos((hour - 18) / 24 * 2 * np.pi)
    return float(diurnal)


def generate_demo_measurements(cfg: DemoConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed)

    start = cfg.start.replace(tzinfo=timezone.utc)
    end = cfg.end.replace(tzinfo=timezone.utc)

    timestamps: list[pd.Timestamp] = []
    lats: list[float] = []
    lons: list[float] = []
    parameters: list[str] = []
    values: list[float] = []
    units: list[str] = []

    min_lon, min_lat, max_lon, max_lat = cfg.bbox

    current = start
    while current <= end:
        ts = pd.Timestamp(current)
        # Sample random points within bbox
        lon_samples = rng.uniform(min_lon, max_lon, cfg.points_per_hour)
        lat_samples = rng.uniform(min_lat, max_lat, cfg.points_per_hour)

        # Base levels per pollutant
        baselines = {"pm25": 60.0, "so2": 20.0, "no2": 40.0}
        amplitudes = {"pm25": 40.0, "so2": 10.0, "no2": 20.0}
        noise_scales = {"pm25": 12.0, "so2": 5.0, "no2": 8.0}
        units_map = {"pm25": "µg/m³", "so2": "µg/m³", "no2": "µg/m³"}

        seasonal = _seasonal_multiplier(ts)
        diurnal = _diurnal_multiplier(ts)

        for pollutant in ("pm25", "so2", "no2"):
            base = baselines[pollutant]
            amp = amplitudes[pollutant]
            noise = rng.normal(0.0, noise_scales[pollutant], cfg.points_per_hour)
            vals = base * seasonal * diurnal + amp * diurnal + noise
            vals = np.clip(vals, a_min=0.0, a_max=None)

            for i in range(cfg.points_per_hour):
                timestamps.append(ts)
                lats.append(float(lat_samples[i]))
                lons.append(float(lon_samples[i]))
                parameters.append(pollutant)
                values.append(float(vals[i]))
                units.append(units_map[pollutant])

        current += timedelta(hours=1)

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "latitude": lats,
            "longitude": lons,
            "parameter": parameters,
            "value": values,
            "unit": units,
            "location": "demo",
            "city": "demo",
            "country": "demo",
        }
    )
    return df


def save_to_csv(df: pd.DataFrame, path: str) -> None:
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
