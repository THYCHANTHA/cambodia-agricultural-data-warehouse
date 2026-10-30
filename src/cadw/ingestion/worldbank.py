"""World Bank Indicators API (v2) ingestion. No API key required."""

from __future__ import annotations

import pandas as pd

from .http import get_with_retry

BASE = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"


def parse_indicator_payload(payload: list, indicator: str) -> pd.DataFrame:
    """Turn one API page [meta, rows] into a flat DataFrame. Null observations are kept as NaN."""
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        message = payload[0] if isinstance(payload, list) and payload else payload
        raise ValueError(f"unexpected World Bank response for {indicator}: {message}")
    rows = [
        {
            "indicator_code": r["indicator"]["id"],
            "indicator_name": r["indicator"]["value"],
            "country_iso3": r["countryiso3code"],
            "country_name": r["country"]["value"],
            "year": r["date"],
            "value": r["value"],
            "unit": r.get("unit", ""),
            "obs_status": r.get("obs_status", ""),
        }
        for r in payload[1]
    ]
    return pd.DataFrame(rows)


def fetch_indicator(
    country: str, indicator: str, *, timeout: int = 120, retries: int = 4
) -> tuple[pd.DataFrame, str]:
    """Fetch every page of one indicator. Returns (data, source 'lastupdated' stamp)."""
    frames: list[pd.DataFrame] = []
    page, last_updated = 1, ""
    while True:
        resp = get_with_retry(
            BASE.format(country=country, indicator=indicator),
            params={"format": "json", "per_page": 100, "page": page},
            timeout=timeout,
            retries=retries,
        )
        payload = resp.json()
        frames.append(parse_indicator_payload(payload, indicator))
        meta = payload[0]
        last_updated = meta.get("lastupdated", last_updated)
        if page >= int(meta["pages"]):
            break
        page += 1
    return pd.concat(frames, ignore_index=True), last_updated


def fetch_indicators(country: str, indicators: list[str], **kwargs) -> tuple[pd.DataFrame, dict[str, str]]:
    frames, stamps = [], {}
    for code in indicators:
        df, stamp = fetch_indicator(country, code, **kwargs)
        frames.append(df)
        stamps[code] = stamp
    return pd.concat(frames, ignore_index=True), stamps
