import io
import zipfile

import pandas as pd
import pytest

from cadw.ingestion import faostat

COLS = faostat.EXPECTED_COLUMNS


def _row(m49, item="Rice", element="Production", year="2020", value="100", flag="A"):
    return [m49, m49, "Somewhere", "27", "'0112", item, "5510", element, year, year, "t", value, flag, ""]


def _frame(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_filter_country_handles_quoted_and_padded_m49_codes():
    chunk = _frame([_row("'116"), _row("'0116"), _row("'004"), _row("116")])
    out = faostat.filter_country([chunk], "116")
    assert len(out) == 3
    assert set(out["Area Code (M49)"]) == {"'116", "'0116", "116"}


def test_filter_country_across_chunks_and_empty_result():
    a, b = _frame([_row("'116")]), _frame([_row("'004")])
    assert len(faostat.filter_country([a, b], "116")) == 1
    assert faostat.filter_country([a, b], "999").empty
    assert faostat.filter_country([], "116").empty


def test_to_bronze_column_names_match_ddl():
    cols = list(faostat.to_bronze(_frame([_row("'116")])).columns)
    assert cols == [
        "area_code",
        "area_code_m49",
        "area",
        "item_code",
        "item_code_cpc",
        "item",
        "element_code",
        "element",
        "year_code",
        "year",
        "unit",
        "value",
        "flag",
        "note",
    ]


def _make_zip(path, data_rows, drop_column=None):
    df = _frame(data_rows)
    if drop_column:
        df = df.drop(columns=[drop_column])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "Production_Crops_Livestock_E_All_Data_(Normalized).csv", buf.getvalue().encode("latin-1")
        )
        zf.writestr("Production_Crops_Livestock_E_Flags.csv", "Flag,Flags\nA,Official figure\n")


def test_read_country_from_zip_roundtrip_keeps_text_and_blank_values(tmp_path):
    z = tmp_path / "f.zip"
    _make_zip(z, [_row("'116", value=""), _row("'116", year="2021", value="12.5"), _row("'004")])
    df = faostat.read_country_from_zip(z, "116", chunksize=2)
    assert len(df) == 2
    assert df["Value"].tolist() == ["", "12.5"]  # blank stays blank: never imputed at ingestion
    lookup = faostat.read_lookup(z, "Flags.csv")
    assert lookup.iloc[0].tolist() == ["A", "Official figure"]


def test_read_country_from_zip_rejects_unexpected_schema(tmp_path):
    z = tmp_path / "bad.zip"
    _make_zip(z, [_row("'116")], drop_column="Flag")
    with pytest.raises(ValueError, match="missing expected columns"):
        faostat.read_country_from_zip(z, "116")
