"""Smoke-test every dashboard page against the real database. Run with:  pytest -m db"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.db
APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
PAGES = ["Overview", "Crop production", "Rainfall", "Indicators", "Data quality", "About"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_error(page):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, f"{page}: {at.exception}"
    assert not at.error, f"{page} showed an error banner: {[e.value for e in at.error]}"


def test_overview_states_the_national_only_limitation():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert any("never inferred" in i.value for i in at.info)


def test_crop_page_defaults_to_rice_and_hides_aggregates():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Crop production").run()
    assert not at.exception
    assert at.multiselect[0].value == ["Rice"]
    options = at.multiselect[0].options
    assert "Cereals, primary" not in options and "Rice" in options
