-- Bronze layer: data exactly as received from each source, plus lineage columns.
-- Idempotent: safe to run repeatedly. No business logic lives here.

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS audit;

-- One row per ingestion run per source: provenance for every Bronze table.
CREATE TABLE IF NOT EXISTS audit.ingestion_log (
    batch_id        UUID        PRIMARY KEY,
    source_name     TEXT        NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'succeeded', 'failed')),
    rows_loaded     BIGINT,
    source_url      TEXT,
    source_version  TEXT,         -- e.g. file Last-Modified, API 'lastupdated'
    source_sha256   TEXT,         -- checksum of the downloaded artefact where one exists
    licence         TEXT,
    notes           TEXT
);

-- FAOSTAT "Crops and livestock products" (normalized layout). All source fields kept as text.
CREATE TABLE IF NOT EXISTS bronze.faostat_production (
    area_code        TEXT, area_code_m49 TEXT, area TEXT,
    item_code        TEXT, item_code_cpc TEXT, item TEXT,
    element_code     TEXT, element TEXT,
    year_code        TEXT, year TEXT,
    unit             TEXT, value TEXT, flag TEXT, note TEXT,
    _batch_id        UUID NOT NULL, _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.faostat_flags (
    flag TEXT, description TEXT, _batch_id UUID NOT NULL, _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- World Bank Indicators API (v2), one row per indicator-year observation.
CREATE TABLE IF NOT EXISTS bronze.worldbank_indicator (
    indicator_code TEXT, indicator_name TEXT, country_iso3 TEXT, country_name TEXT,
    year TEXT, value DOUBLE PRECISION, unit TEXT, obs_status TEXT,
    _batch_id UUID NOT NULL, _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- geoBoundaries ADM1 provinces. Geometry stored as GeoJSON text (no PostGIS dependency).
CREATE TABLE IF NOT EXISTS bronze.geoboundaries_adm1 (
    shape_id TEXT, shape_name TEXT, shape_iso TEXT, shape_group TEXT, shape_type TEXT,
    geometry_geojson TEXT,
    _batch_id UUID NOT NULL, _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CHIRPS v3.0 monthly rainfall aggregated to province (rasters are not retained; see chirps.py).
CREATE TABLE IF NOT EXISTS bronze.chirps_province_monthly (
    year INTEGER, month INTEGER, source_url TEXT, province_key TEXT,
    precip_mean_mm DOUBLE PRECISION, precip_min_mm DOUBLE PRECISION, precip_max_mm DOUBLE PRECISION,
    n_pixels INTEGER, n_valid_pixels INTEGER, mask_method TEXT,
    _batch_id UUID NOT NULL, _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
