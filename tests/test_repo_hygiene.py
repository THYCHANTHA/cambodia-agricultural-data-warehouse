"""Guards against committing credentials or data. These run in CI and locally."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if (ROOT / line).is_file()]


def test_env_example_has_no_password():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    match = re.search(r"^CADW_DB_PASSWORD=(.*)$", text, flags=re.MULTILINE)
    assert match is not None and match.group(1).strip() == "", (
        "type your password into .env, never .env.example"
    )


def test_real_env_file_is_not_tracked():
    names = {p.name for p in _tracked_files()}
    assert ".env" not in names


def test_no_data_or_environment_artefacts_are_tracked():
    bad = [
        p.relative_to(ROOT).as_posix()
        for p in _tracked_files()
        if re.search(
            r"(^|/)(data/raw|\.venv|\.venv-dbt|dbt/target)/|\.(zip|tif|tiff|parquet)$",
            p.relative_to(ROOT).as_posix(),
        )
    ]
    assert bad == []


def test_no_secret_patterns_in_tracked_text_files():
    patterns = re.compile(
        r"(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pous]_[A-Za-z0-9]{30,}|BEGIN [A-Z ]*PRIVATE KEY)"
    )
    hits = []
    for p in _tracked_files():
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if patterns.search(text):
            hits.append(p.name)
    assert hits == []


def test_a_password_assignment_never_has_a_value_in_tracked_files():
    hits = []
    for p in _tracked_files():
        if p.name == "test_repo_hygiene.py":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in re.finditer(r"(?m)^[ \t]*[A-Z][A-Z_]*PASSWORD[ \t]*=[ \t]*(\S+)", text):
            hits.append((p.name, m.group(0).split("=")[0].strip()))
    assert hits == []
