from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

import pandas as pd
import requests


OPENAQ_BASE_URL = "https://api.openaq.org/v2/measurements"


@dataclass(frozen=True)
class OpenAQQuery:
    parameters: tuple[str, ...] = ("pm25", "so2", "no2")
    city: Optional[str] = None
    country: Optional[str] = None
    bbox: Optional[tuple[float, float, float, float]] = None  # (min_lon, min_lat, max_lon, max_lat)
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit_per_page: int = 1000
    max_pages: int = 5


def _to_iso(dt: datetime | str | None) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        # Assume already ISO formatted
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def fetch_measurements(query: OpenAQQuery) -> pd.DataFrame:
    """
    Fetch measurements from OpenAQ v2 API according to the query.

    Returns a DataFrame with columns:
      ['timestamp','latitude','longitude','parameter','value','unit','location','city','country']
    """
    all_rows: list[dict] = []

    params: dict[str, object] = {
        "limit": query.limit_per_page,
        "sort": "desc",
    }
    if query.parameters:
        params["parameter"] = ",".join(query.parameters)
    if query.city:
        params["city"] = query.city
    if query.country:
        params["country"] = query.country
    if query.bbox:
        min_lon, min_lat, max_lon, max_lat = query.bbox
        params["bbox"] = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    if query.start:
        params["date_from"] = _to_iso(query.start)
    if query.end:
        params["date_to"] = _to_iso(query.end)

    session = requests.Session()

    for page in range(1, query.max_pages + 1):
        params["page"] = page
        try:
            resp = session.get(OPENAQ_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            # Return what we have so far
            break

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for r in results:
            coordinates = r.get("coordinates") or {}
            # Prefer utc time string if present
            date_info = r.get("date") or {}
            timestamp = (
                date_info.get("utc")
                or date_info.get("local")
                or r.get("dateTime")
            )
            all_rows.append(
                {
                    "timestamp": timestamp,
                    "latitude": coordinates.get("latitude"),
                    "longitude": coordinates.get("longitude"),
                    "parameter": r.get("parameter"),
                    "value": r.get("value"),
                    "unit": r.get("unit"),
                    "location": r.get("location"),
                    "city": r.get("city"),
                    "country": r.get("country"),
                }
            )

        # If we received fewer than limit, likely last page
        if len(results) < int(params["limit"]):
            break

    if not all_rows:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "latitude",
                "longitude",
                "parameter",
                "value",
                "unit",
                "location",
                "city",
                "country",
            ]
        )

    df = pd.DataFrame(all_rows)
    # Normalize timestamp to pandas datetime (UTC if possible)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    # Drop missing coordinates or values
    df = df.dropna(subset=["latitude", "longitude", "value", "timestamp"]).reset_index(drop=True)
    return df


def save_to_csv(df: pd.DataFrame, path: str) -> None:
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
