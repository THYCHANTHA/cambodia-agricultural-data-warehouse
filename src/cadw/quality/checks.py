"""Source-level data-quality checks run on Bronze frames *before* they are loaded.

Each check returns a CheckResult; nothing here mutates data. Results are persisted to
audit.data_quality_results so that every pipeline run leaves an inspectable trail.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class CheckResult:
    source: str
    check: str
    passed: bool
    n_violations: int
    detail: str = ""
    severity: str = "error"  # 'error' fails the pipeline; 'warning' is recorded only

    def as_dict(self) -> dict:
        return asdict(self)


def required_columns(df: pd.DataFrame, source: str, columns: list[str]) -> CheckResult:
    missing = [c for c in columns if c not in df.columns]
    return CheckResult(
        source, "required_columns", not missing, len(missing), f"missing: {missing}" if missing else ""
    )


def not_empty(df: pd.DataFrame, source: str) -> CheckResult:
    return CheckResult(source, "not_empty", len(df) > 0, int(len(df) == 0), f"rows={len(df)}")


def no_duplicate_keys(df: pd.DataFrame, source: str, keys: list[str]) -> CheckResult:
    n = int(df.duplicated(subset=keys, keep=False).sum())
    return CheckResult(source, f"no_duplicate_keys({','.join(keys)})", n == 0, n)


def value_range(df: pd.DataFrame, source: str, column: str, low: float, high: float) -> CheckResult:
    vals = pd.to_numeric(df[column], errors="coerce").dropna()
    n = int(((vals < low) | (vals > high)).sum())
    return CheckResult(source, f"range({column}:{low}..{high})", n == 0, n)


def year_window(df: pd.DataFrame, source: str, column: str, low: int, high: int) -> CheckResult:
    years = pd.to_numeric(df[column], errors="coerce")
    bad = int(years.isna().sum() + ((years < low) | (years > high)).sum())
    return CheckResult(source, f"year_window({column}:{low}..{high})", bad == 0, bad)


def missing_share(df: pd.DataFrame, source: str, column: str, max_share: float) -> CheckResult:
    """Missing values are legitimate in statistics, so this is a warning, not an error."""
    s = df[column]
    blank = s.isna() | (s.astype(str).str.strip() == "")
    share = float(blank.mean()) if len(df) else 1.0
    return CheckResult(
        source,
        f"missing_share({column}<={max_share:.0%})",
        share <= max_share,
        int(blank.sum()),
        f"share={share:.2%}",
        severity="warning",
    )


def expected_count(df: pd.DataFrame, source: str, expected: int, label: str) -> CheckResult:
    return CheckResult(
        source,
        f"expected_count({label}={expected})",
        len(df) == expected,
        abs(len(df) - expected),
        f"rows={len(df)}",
    )


def chirps_completeness(
    df: pd.DataFrame, n_provinces: int, start_year: int, end_year: int, failures: list
) -> CheckResult:
    expected = n_provinces * 12 * (end_year - start_year + 1)
    got = len(df)
    return CheckResult(
        "chirps_province_monthly",
        "completeness",
        got == expected and not failures,
        abs(expected - got),
        f"expected={expected} got={got} failed_months={len(failures)}",
    )


def summarise(results: list[CheckResult]) -> tuple[bool, str]:
    failed = [r for r in results if not r.passed and r.severity == "error"]
    warned = [r for r in results if not r.passed and r.severity == "warning"]
    lines = [f"{len(results)} checks, {len(failed)} errors, {len(warned)} warnings"]
    lines += [f"  ERROR   {r.source}: {r.check} ({r.n_violations}) {r.detail}" for r in failed]
    lines += [f"  WARNING {r.source}: {r.check} ({r.n_violations}) {r.detail}" for r in warned]
    return (not failed), "\n".join(lines)
