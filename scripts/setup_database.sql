-- One-off setup. Run ONCE as the PostgreSQL superuser, e.g.
--   psql -h localhost -U postgres -f sql/setup_database.sql
-- Replace the placeholder password first, then put the same value in .env as CADW_DB_PASSWORD.
-- The project role owns only its own database and has no superuser rights.

CREATE ROLE cadw LOGIN PASSWORD 'REPLACE_WITH_A_STRONG_PASSWORD' NOSUPERUSER NOCREATEROLE;
CREATE DATABASE cambodia_dw OWNER cadw;
