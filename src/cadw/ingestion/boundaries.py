"""Province (ADM1) boundaries for Cambodia from geoBoundaries (gbOpen, ODbL 1.0)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .http import download_file, get_with_retry

API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM1/"


def resolve_release(iso3: str) -> dict:
    """Ask the geoBoundaries API for the current release metadata (URL, year, licence)."""
    meta = get_with_retry(API.format(iso3=iso3)).json()
    for key in ("gjDownloadURL", "boundaryLicense", "boundaryYearRepresented"):
        if key not in meta:
            raise ValueError(f"geoBoundaries metadata missing '{key}'")
    return meta


def download_adm1(iso3: str, raw_dir: Path) -> tuple[Path, dict]:
    meta = resolve_release(iso3)
    dest = raw_dir / "boundaries" / f"geoBoundaries-{iso3}-ADM1.geojson"
    info = download_file(meta["gjDownloadURL"], dest)
    return dest, {**info, "licence": meta["boundaryLicense"], "year": meta["boundaryYearRepresented"]}


def load_adm1_table(geojson_path: Path) -> pd.DataFrame:
    """Flatten the GeoJSON into one row per province with the geometry kept as a GeoJSON string."""
    data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    rows = []
    for feat in data["features"]:
        props = feat["properties"]
        rows.append(
            {
                "shape_id": props.get("shapeID"),
                "shape_name": props.get("shapeName"),
                "shape_iso": props.get("shapeISO"),
                "shape_group": props.get("shapeGroup"),
                "shape_type": props.get("shapeType"),
                "geometry_geojson": json.dumps(feat["geometry"]),
            }
        )
    df = pd.DataFrame(rows)
    if df["shape_id"].isna().any() or df["shape_name"].isna().any():
        raise ValueError("boundary file has features without shapeID/shapeName")
    return df
