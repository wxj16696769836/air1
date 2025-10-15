from __future__ import annotations

import time
from typing import Dict, List, Optional

import pandas as pd
import requests
from loguru import logger

from .config import FetchConfig

OPENAQ_V2 = "https://api.openaq.org/v2/measurements"
OPENAQ_V3 = "https://api.openaq.org/v3/measurements"


def _build_params_v2(cfg: FetchConfig, page: int) -> Dict[str, str]:
    params: Dict[str, str] = {
        "page": str(page),
        "limit": str(min(cfg.limit, 10000)),
        "sort": "desc",
        "order_by": "datetime",
    }
    if cfg.city:
        params["city"] = cfg.city
    if cfg.country:
        params["country"] = cfg.country
    if cfg.bbox:
        params["coordinates"] = f"{cfg.bbox[1]},{cfg.bbox[0]};{cfg.bbox[3]},{cfg.bbox[2]}"  # lat,lon;lat,lon
        params["radius"] = "100000"
    if cfg.start:
        params["date_from"] = cfg.start
    if cfg.end:
        params["date_to"] = cfg.end
    if cfg.parameters:
        params["parameter[]"] = cfg.parameters
    return params


def _build_params_v3(cfg: FetchConfig, page: int) -> Dict[str, str]:
    # OpenAQ v3 parameterization differs; see docs. We'll use common filters.
    params: Dict[str, str] = {
        "page": str(page),
        "limit": str(min(cfg.limit, 10000)),
        "sort": "-datetime",
    }
    if cfg.city:
        params["city"] = cfg.city
    if cfg.country:
        params["country"] = cfg.country
    if cfg.bbox:
        # v3 uses bbox=west,south,east,north
        params["bbox"] = f"{cfg.bbox[0]},{cfg.bbox[1]},{cfg.bbox[2]},{cfg.bbox[3]}"
    if cfg.start:
        params["datetime_from"] = cfg.start
    if cfg.end:
        params["datetime_to"] = cfg.end
    if cfg.parameters:
        params["parameters[]"] = cfg.parameters
    return params


def fetch_openaq(cfg: FetchConfig, max_pages: int = 5, sleep_s: float = 0.2) -> pd.DataFrame:
    """Fetch measurements from OpenAQ API (v3 preferred, fallback to v2 if possible).

    Returns a DataFrame with columns: latitude, longitude, parameter, value, unit, datetime, location, city, country.
    """
    headers = {}
    use_v3 = cfg.api_key is not None
    if use_v3:
        headers["X-API-Key"] = cfg.api_key  # v3 requires API key

    all_rows: List[Dict] = []
    for page in range(1, max_pages + 1):
        params = _build_params_v3(cfg, page) if use_v3 else _build_params_v2(cfg, page)
        base = OPENAQ_V3 if use_v3 else OPENAQ_V2
        logger.info(f"Fetching OpenAQ {'v3' if use_v3 else 'v2'} page {page} with params: {params}")
        resp = requests.get(base, params=params, headers=headers, timeout=60)
        if resp.status_code == 401 and use_v3:
            logger.error("OpenAQ v3 requires a valid API key. Set FetchConfig.api_key or OPENAQ_API_KEY.")
            break
        if resp.status_code == 410 and use_v3 is False:
            logger.warning("OpenAQ v2 endpoint is deprecated (410). Provide an API key to use v3.")
            break
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        for r in results:
            # v3 structure: coordinates under 'coordinates' or 'location.coordinates'; use robust access
            coords = r.get("coordinates") or r.get("location", {}).get("coordinates") or {}
            dt = r.get("datetime") or r.get("date", {}).get("utc")
            all_rows.append(
                {
                    "latitude": coords.get("latitude"),
                    "longitude": coords.get("longitude"),
                    "parameter": r.get("parameter"),
                    "value": r.get("value"),
                    "unit": r.get("unit"),
                    "datetime": dt,
                    "location": r.get("location") if isinstance(r.get("location"), str) else r.get("location", {}).get("name"),
                    "city": r.get("city"),
                    "country": r.get("country"),
                }
            )
        meta = data.get("meta", {})
        found = meta.get("found", 0)
        limit = meta.get("limit", cfg.limit)
        if page * limit >= found:
            break
        time.sleep(sleep_s)

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.dropna(subset=["latitude", "longitude", "value", "parameter"]).reset_index(drop=True)
    return df
