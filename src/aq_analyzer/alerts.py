from __future__ import annotations

from typing import Dict

import pandas as pd


def generate_alerts(df: pd.DataFrame, thresholds: Dict[str, float]) -> pd.DataFrame:
    """Return rows where value exceeds thresholds per parameter."""
    alerts = []
    for param, thr in thresholds.items():
        subset = df[(df["parameter"] == param) & (df["value"] > thr)]
        if not subset.empty:
            subset = subset.copy()
            subset["threshold"] = thr
            alerts.append(subset)
    if alerts:
        return pd.concat(alerts, ignore_index=True)
    return pd.DataFrame(columns=list(df.columns) + ["threshold"])