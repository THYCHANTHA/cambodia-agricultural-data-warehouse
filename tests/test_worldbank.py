import pytest

from cadw.ingestion import worldbank


def _payload(values):
    meta = {"page": 1, "pages": 1, "per_page": 100, "total": len(values), "lastupdated": "2026-10-08"}
    rows = [
        {
            "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
            "country": {"id": "KH", "value": "Cambodia"},
            "countryiso3code": "KHM",
            "date": str(2000 + i),
            "value": v,
            "unit": "",
            "obs_status": "",
            "decimal": 0,
        }
        for i, v in enumerate(values)
    ]
    return [meta, rows]


def test_parse_keeps_null_observations_as_missing():
    df = worldbank.parse_indicator_payload(_payload([1.0, None, 3.0]), "SP.POP.TOTL")
    assert len(df) == 3
    assert df["value"].isna().tolist() == [False, True, False]
    assert set(df["country_iso3"]) == {"KHM"}
    assert df["year"].tolist() == ["2000", "2001", "2002"]


@pytest.mark.parametrize(
    "bad",
    [
        [
            {
                "message": [
                    {
                        "id": "120",
                        "key": "Invalid value",
                        "value": "The provided parameter value is not valid",
                    }
                ]
            }
        ],
        [{"page": 1}, None],
        {"unexpected": "dict"},
    ],
)
def test_parse_rejects_error_payloads(bad):
    with pytest.raises(ValueError, match="unexpected World Bank response"):
        worldbank.parse_indicator_payload(bad, "XX")
