import numpy as np
import pytest
from rasterio.transform import from_origin

from cadw.ingestion import chirps

# 10x10 grid of 1-degree pixels, origin at lon 100, lat 20 (north-up).
T = from_origin(100.0, 20.0, 1.0, 1.0)


def box(x0, y0, x1, y1):
    return {"type": "Polygon", "coordinates": [[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]}


def test_monthly_url_pads_month():
    assert chirps.monthly_url("https://h/tifs", 2023, 7) == "https://h/tifs/chirps-v3.0.2023.07.tif"


def test_months_covers_every_month_once():
    ms = list(chirps.months(2000, 2001))
    assert len(ms) == 24 and ms[0] == (2000, 1) and ms[-1] == (2001, 12)


def test_province_stats_mean_min_max_and_pixel_counts():
    data = np.full((10, 10), 100.0)
    data[0:2, 0:2] = [[10.0, 20.0], [30.0, 40.0]]  # top-left 2x2 block
    (res,) = chirps.province_stats(data, T, {"A": box(100, 18, 102, 20)}, nodata=-9999.0)
    assert res["n_pixels"] == 4 and res["n_valid_pixels"] == 4
    assert res["precip_mean_mm"] == pytest.approx(25.0)
    assert (res["precip_min_mm"], res["precip_max_mm"]) == (10.0, 40.0)
    assert res["mask_method"] == "pixel_centre"


def test_province_stats_excludes_nodata_but_reports_coverage():
    data = np.full((10, 10), 50.0)
    data[0, 0] = -9999.0  # NoData pixel inside the province
    (res,) = chirps.province_stats(data, T, {"A": box(100, 18, 102, 20)}, nodata=-9999.0)
    assert res["n_pixels"] == 4 and res["n_valid_pixels"] == 3
    assert res["precip_mean_mm"] == pytest.approx(50.0)  # nodata must not drag the mean down


def test_province_stats_all_nodata_gives_null_not_zero():
    data = np.full((10, 10), -9999.0)
    (res,) = chirps.province_stats(data, T, {"A": box(100, 18, 102, 20)}, nodata=-9999.0)
    assert res["precip_mean_mm"] is None and res["n_valid_pixels"] == 0


def test_tiny_province_falls_back_to_all_touched_instead_of_being_dropped():
    data = np.full((10, 10), 7.0)
    tiny = box(100.1, 19.1, 100.3, 19.3)  # inside pixel (0,0) but away from its centre (100.5, 19.5)
    (res,) = chirps.province_stats(data, T, {"tiny": tiny}, nodata=-9999.0)
    assert res["mask_method"] == "all_touched"
    assert res["n_pixels"] >= 1 and res["precip_mean_mm"] == pytest.approx(7.0)


def test_each_province_gets_its_own_row():
    data = np.arange(100, dtype="float64").reshape(10, 10)
    geoms = {"W": box(100, 15, 103, 20), "E": box(107, 15, 110, 20)}
    rows = chirps.province_stats(data, T, geoms, nodata=None)
    assert [r["province_key"] for r in rows] == ["W", "E"]
    assert rows[0]["precip_mean_mm"] != rows[1]["precip_mean_mm"]


@pytest.mark.network
def test_read_real_month_for_all_provinces():
    """Live check against CHIRPS v3.0 (slow). Run with: pytest -m network"""
    from cadw.config import get_settings
    from cadw.ingestion import boundaries

    settings = get_settings()
    path, _ = boundaries.download_adm1("KHM", settings.raw_dir)
    geoms = chirps.province_geometries(boundaries.load_adm1_table(path))
    rows = chirps.read_month(chirps.monthly_url(settings.chirps_base_url, 2023, 7), geoms)
    assert len(rows) == 25
    assert all(0 <= r["precip_mean_mm"] < 2500 for r in rows)
