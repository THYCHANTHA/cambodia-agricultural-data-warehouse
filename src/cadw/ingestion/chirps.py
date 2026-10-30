"""CHIRPS v3.0 monthly rainfall -> province-month aggregates.

Each global monthly GeoTIFF is ~21 MB and the full archive (1981-present) is ~12 GB, so rasters
are never stored. Each month is read through GDAL's HTTP range reader (/vsicurl/), only the
Cambodia window is decoded, and per-province statistics are kept. Raw rasters are therefore NOT
part of the Bronze layer; the Bronze table holds the province aggregates plus pixel counts.

CHIRPS monthly values are precipitation totals in mm/month. NoData is read from the file.
Reference: Funk et al. (2015) doi:10.1038/sdata.2015.66 (CHIRPS v2); CHIRPS v3 documentation at
https://www.chc.ucsb.edu/data/chirps3
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

log = logging.getLogger(__name__)

# Padded Cambodia bounding box (lon_min, lat_min, lon_max, lat_max) used to window the global grid.
CAMBODIA_BBOX = (102.2, 9.9, 107.7, 14.8)


def monthly_url(base_url: str, year: int, month: int) -> str:
    return f"{base_url}/chirps-v3.0.{year}.{month:02d}.tif"


def province_stats(
    data: np.ndarray, transform, geometries: dict[str, dict], nodata: float | None
) -> list[dict]:
    """Aggregate one raster window per province polygon.

    A pixel belongs to a province if its centre lies inside it. Provinces smaller than a pixel
    fall back to `all_touched=True` so that none is silently dropped; `n_pixels` documents this.
    Returns one dict per province: mean/min/max mm, n_pixels, n_valid_pixels.
    """
    out = []
    valid_all = np.isfinite(data) & (data != nodata if nodata is not None else True) & (data >= 0)
    for key, geom in geometries.items():
        mask = ~geometry_mask([geom], out_shape=data.shape, transform=transform, all_touched=False)
        method = "pixel_centre"
        if not mask.any():
            mask = ~geometry_mask([geom], out_shape=data.shape, transform=transform, all_touched=True)
            method = "all_touched"
        n_pixels = int(mask.sum())
        vals = data[mask & valid_all]
        out.append(
            {
                "province_key": key,
                "precip_mean_mm": float(vals.mean()) if vals.size else None,
                "precip_min_mm": float(vals.min()) if vals.size else None,
                "precip_max_mm": float(vals.max()) if vals.size else None,
                "n_pixels": n_pixels,
                "n_valid_pixels": int(vals.size),
                "mask_method": method,
            }
        )
    return out


def read_month(url: str, geometries: dict[str, dict], bbox=CAMBODIA_BBOX) -> list[dict]:
    """Read the Cambodia window of one remote CHIRPS GeoTIFF and aggregate per province."""
    with rasterio.Env(
        GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"
    ):
        with rasterio.open(f"/vsicurl/{url}") as src:
            window = from_bounds(*bbox, transform=src.transform)
            data = src.read(1, window=window, masked=False).astype("float64")
            transform = src.window_transform(window)
            return province_stats(data, transform, geometries, src.nodata)


def province_geometries(boundary_df: pd.DataFrame) -> dict[str, dict]:
    """Map province key (shape_id) -> shapely-compatible GeoJSON geometry mapping."""
    import json

    return {r.shape_id: json.loads(r.geometry_geojson) for r in boundary_df.itertuples()}


def months(start_year: int, end_year: int) -> Iterable[tuple[int, int]]:
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            yield y, m


def ingest(
    base_url: str, periods: Iterable[tuple[int, int]], geometries: dict[str, dict], *, workers: int = 4
) -> pd.DataFrame:
    """Aggregate every month in the window (I/O bound, so threaded).

    Months that fail after retries are reported in `df.attrs["failures"]`, never silently dropped.
    """
    rows: list[dict] = []
    failures: list[tuple[int, int, str]] = []

    def one(ym: tuple[int, int]) -> tuple[tuple[int, int], list[dict] | Exception]:
        url = monthly_url(base_url, *ym)
        try:
            return ym, [
                {"year": ym[0], "month": ym[1], "source_url": url, **r} for r in read_month(url, geometries)
            ]
        except Exception as exc:  # network/GDAL errors vary widely; collect and surface them
            return ym, exc

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for (year, month), result in pool.map(one, list(periods)):
            if isinstance(result, Exception):
                log.error("CHIRPS %d-%02d failed: %s", year, month, result)
                failures.append((year, month, str(result)))
            else:
                rows.extend(result)
    df = pd.DataFrame(rows)
    df.attrs["failures"] = failures
    return df
