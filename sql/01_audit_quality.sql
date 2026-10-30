-- Results of source-level data-quality checks, one row per check per ingestion batch.
CREATE TABLE IF NOT EXISTS audit.data_quality_results (
    id           BIGSERIAL PRIMARY KEY,
    batch_id     UUID        NOT NULL,
    source_name  TEXT        NOT NULL,
    check_name   TEXT        NOT NULL,
    passed       BOOLEAN     NOT NULL,
    n_violations BIGINT      NOT NULL,
    severity     TEXT        NOT NULL,
    detail       TEXT,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
