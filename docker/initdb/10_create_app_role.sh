#!/bin/bash
# Runs once when the Postgres container first initialises its data directory.
# Creates the least-privilege application role and database (the password comes from the environment).
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
CREATE ROLE cadw LOGIN PASSWORD '${CADW_DB_PASSWORD}' NOSUPERUSER NOCREATEROLE NOCREATEDB;
CREATE DATABASE cambodia_dw OWNER cadw;
SQL
