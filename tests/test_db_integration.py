"""Integration tests against the real PostgreSQL instance. Run with:  pytest -m db"""

import uuid

import pandas as pd
import pytest
from sqlalchemy import text

from cadw import warehouse
from cadw.config import get_settings

pytestmark = pytest.mark.db


@pytest.fixture()
def engine():
    eng = warehouse.make_engine(get_settings())
    with eng.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA IF EXISTS cadw_test CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA cadw_test")
        conn.exec_driver_sql(
            "CREATE TABLE cadw_test.t (a TEXT, b DOUBLE PRECISION, _batch_id UUID NOT NULL,"
            " _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
    yield eng
    with eng.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA IF EXISTS cadw_test CASCADE")


def test_load_bronze_writes_uuid_lineage_and_replaces_contents(engine):
    batch = uuid.uuid4()
    warehouse.load_bronze(
        engine, "t", pd.DataFrame({"a": ["x", "y"], "b": [1.0, None]}), batch, schema="cadw_test"
    )
    warehouse.load_bronze(engine, "t", pd.DataFrame({"a": ["z"], "b": [3.0]}), batch, schema="cadw_test")
    with engine.connect() as conn:
        rows = conn.execute(text("select a, _batch_id from cadw_test.t")).all()
    assert [r[0] for r in rows] == ["z"]  # full refresh, not append
    assert rows[0][1] == batch


def test_failed_load_rolls_back_and_keeps_previous_data(engine):
    batch = uuid.uuid4()
    warehouse.load_bronze(engine, "t", pd.DataFrame({"a": ["keep"], "b": [1.0]}), batch, schema="cadw_test")
    bad = pd.DataFrame({"a": ["new"], "b": ["not-a-number"]})
    with pytest.raises(Exception):  # noqa: B017 - any DB error must abort the whole load
        warehouse.load_bronze(engine, "t", bad, batch, schema="cadw_test")
    with engine.connect() as conn:
        assert conn.execute(text("select a from cadw_test.t")).scalars().all() == ["keep"]


def test_empty_frame_is_refused(engine):
    with pytest.raises(ValueError, match="empty"):
        warehouse.load_bronze(engine, "t", pd.DataFrame({"a": [], "b": []}), uuid.uuid4(), schema="cadw_test")


def test_ddl_is_idempotent_and_role_is_not_superuser(engine):
    warehouse.apply_ddl(engine)
    warehouse.apply_ddl(engine)
    with engine.connect() as conn:
        assert (
            conn.execute(text("select rolsuper from pg_roles where rolname = current_user")).scalar() is False
        )
        schemas = set(conn.execute(text("select schema_name from information_schema.schemata")).scalars())
    assert {"bronze", "silver", "gold", "audit"} <= schemas
