from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping

import pandas as pd


@dataclass(frozen=True)
class Thresholds:
    values: Mapping[str, float]


DEFAULT_THRESHOLDS = Thresholds(values={
    "pm25": 150.0,  # heavy pollution
    "so2": 350.0,   # example WHO guideline exceedance threshold (placeholder)
    "no2": 200.0,   # example hourly threshold
})


def compute_alerts(df: pd.DataFrame, thresholds: Thresholds = DEFAULT_THRESHOLDS) -> pd.DataFrame:
    required_cols = {"timestamp", "latitude", "longitude", "parameter", "value"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    alerts = df[df.apply(lambda r: r["value"] > thresholds.values.get(str(r["parameter"]).lower(), float("inf")), axis=1)].copy()
    alerts["threshold"] = alerts["parameter"].str.lower().map(thresholds.values)
    alerts["excess"] = alerts["value"] - alerts["threshold"]
    alerts = alerts.sort_values(["timestamp", "parameter"], ascending=[True, True])
    return alerts


def save_alerts(alerts: pd.DataFrame, output_csv: str) -> None:
    p = Path(output_csv)
    p.parent.mkdir(parents=True, exist_ok=True)
    alerts.to_csv(p, index=False)


def summarize_alerts(alerts: pd.DataFrame) -> pd.DataFrame:
    if alerts.empty:
        return pd.DataFrame(columns=["parameter", "count"])
    summary = alerts.groupby("parameter").size().reset_index(name="count")
    return summary
