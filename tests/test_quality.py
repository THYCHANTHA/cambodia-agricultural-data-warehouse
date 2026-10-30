import pandas as pd

from cadw.quality import checks


def test_duplicate_keys_flags_every_member_of_a_duplicate_pair():
    df = pd.DataFrame({"k": [1, 1, 2], "y": [2000, 2000, 2000]})
    r = checks.no_duplicate_keys(df, "s", ["k", "y"])
    assert not r.passed and r.n_violations == 2


def test_year_window_counts_unparseable_and_out_of_range():
    df = pd.DataFrame({"year": ["1999", "2000", "abc", "2101"]})
    r = checks.year_window(df, "s", "year", 2000, 2100)
    assert not r.passed and r.n_violations == 3


def test_missing_share_is_a_warning_not_an_error():
    df = pd.DataFrame({"v": ["1", "", None, "4"]})
    r = checks.missing_share(df, "s", "v", 0.10)
    assert not r.passed and r.severity == "warning" and r.n_violations == 2
    ok, _ = checks.summarise([r])
    assert ok  # warnings never fail the pipeline


def test_value_range_ignores_nulls_and_catches_outliers():
    df = pd.DataFrame({"p": [0.0, 120.0, None, 9999.0, -1.0]})
    r = checks.value_range(df, "s", "p", 0, 2500)
    assert r.n_violations == 2


def test_not_empty_and_required_columns():
    assert not checks.not_empty(pd.DataFrame({"a": []}), "s").passed
    assert checks.required_columns(pd.DataFrame({"a": [1]}), "s", ["a"]).passed
    assert not checks.required_columns(pd.DataFrame({"a": [1]}), "s", ["a", "b"]).passed


def test_chirps_completeness_detects_missing_months_and_failures():
    full = pd.DataFrame({"x": range(25 * 12 * 2)})
    assert checks.chirps_completeness(full, 25, 2000, 2001, []).passed
    assert not checks.chirps_completeness(full.iloc[:-1], 25, 2000, 2001, []).passed
    assert not checks.chirps_completeness(full, 25, 2000, 2001, [(2000, 1, "timeout")]).passed


def test_summarise_reports_errors():
    bad = checks.CheckResult("src", "not_empty", False, 1, "rows=0")
    ok, text = checks.summarise([bad])
    assert not ok and "ERROR" in text and "src" in text
