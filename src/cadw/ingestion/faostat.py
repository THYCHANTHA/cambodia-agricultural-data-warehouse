"""FAOSTAT bulk-file ingestion (Crops and livestock products, normalized layout).

The REST API requires authentication, so the public bulk download is used. The full file is
~545 MB uncompressed; it is streamed in chunks and filtered to the target country.
Source: https://www.fao.org/faostat/en/#data/QCL  (see docs/data_sources.md for licence terms)
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

FAOSTAT_URL = (
    "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip"
)
DATA_MEMBER_HINT = "All_Data"
M49_COLUMN = "Area Code (M49)"
EXPECTED_COLUMNS = [
    "Area Code",
    "Area Code (M49)",
    "Area",
    "Item Code",
    "Item Code (CPC)",
    "Item",
    "Element Code",
    "Element",
    "Year Code",
    "Year",
    "Unit",
    "Value",
    "Flag",
    "Note",
]


def _clean_m49(series: pd.Series) -> pd.Series:
    """FAOSTAT writes M49 codes as quoted text such as "'116"; strip quotes and padding."""
    return series.astype(str).str.replace("'", "", regex=False).str.strip().str.lstrip("0")


def filter_country(chunks, m49: str) -> pd.DataFrame:
    """Keep rows for one country from an iterable of raw (all-text) DataFrame chunks."""
    target = m49.lstrip("0")
    kept = [c[_clean_m49(c[M49_COLUMN]) == target] for c in chunks]
    if not kept:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    return pd.concat(kept, ignore_index=True)


def read_country_from_zip(zip_path: Path, m49: str, chunksize: int = 500_000) -> pd.DataFrame:
    """Stream the bulk CSV inside the zip and return only rows for `m49` (all columns as text)."""
    with zipfile.ZipFile(zip_path) as zf:
        member = next(n for n in zf.namelist() if DATA_MEMBER_HINT in n and n.endswith(".csv"))
        with zf.open(member) as fh:
            chunks = pd.read_csv(
                fh, encoding="latin-1", chunksize=chunksize, dtype=str, keep_default_na=False
            )
            df = filter_country(chunks, m49)
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"FAOSTAT file is missing expected columns: {sorted(missing)}")
    return df[EXPECTED_COLUMNS]


def read_lookup(zip_path: Path, suffix: str) -> pd.DataFrame:
    """Read one of the small lookup CSVs (Flags, ItemCodes, Elements, AreaCodes) from the zip."""
    with zipfile.ZipFile(zip_path) as zf:
        member = next(n for n in zf.namelist() if n.endswith(suffix))
        with zf.open(member) as fh:
            return pd.read_csv(fh, encoding="latin-1", dtype=str, keep_default_na=False)


def to_bronze(df: pd.DataFrame) -> pd.DataFrame:
    """Rename source headers to snake_case column names used by bronze.faostat_production."""
    return df.rename(columns=lambda c: c.lower().replace(" (", "_").replace(")", "").replace(" ", "_"))
