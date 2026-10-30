import json
import os

import pytest

from cadw.config import Settings
from cadw.ingestion import boundaries


def _geojson(features):
    return {"type": "FeatureCollection", "features": features}


def _feat(shape_id, name):
    return {
        "type": "Feature",
        "properties": {
            "shapeID": shape_id,
            "shapeName": name,
            "shapeISO": "KH-1",
            "shapeGroup": "KHM",
            "shapeType": "ADM1",
        },
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    }


def test_load_adm1_table_flattens_and_keeps_geometry(tmp_path):
    p = tmp_path / "b.geojson"
    p.write_text(json.dumps(_geojson([_feat("a", "Kep"), _feat("b", "Pailin")])), encoding="utf-8")
    df = boundaries.load_adm1_table(p)
    assert df["shape_name"].tolist() == ["Kep", "Pailin"]
    assert json.loads(df.loc[0, "geometry_geojson"])["type"] == "Polygon"


def test_load_adm1_table_rejects_features_without_ids(tmp_path):
    p = tmp_path / "b.geojson"
    p.write_text(json.dumps(_geojson([_feat(None, "Kep")])), encoding="utf-8")
    with pytest.raises(ValueError, match="shapeID"):
        boundaries.load_adm1_table(p)


def test_database_url_escapes_special_characters_and_hides_password():
    s = Settings(db_password="p@ss:w/rd#1", _env_file=None)
    url = s.database_url
    assert url.password == "p@ss:w/rd#1"
    assert "p@ss" not in url.render_as_string(hide_password=True)
    assert "p@ss" not in repr(s)


def test_defaults_do_not_ship_a_password(monkeypatch):
    for name in list(os.environ):
        if name.startswith("CADW_"):
            monkeypatch.delenv(name)  # isolate from the developer's real environment
    assert Settings(_env_file=None).db_password == ""
