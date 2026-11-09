"""README honesty contract: problem statement, status, and drift gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from effective_context_lab import __version__
from effective_context_lab.recompute import (
    count_test_functions,
    extract_claims_block,
    find_absolute_paths,
    render_claims,
    tally_data_dir,
)

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _section_body(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index(heading) + 1
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("#"):
            break
        if line.strip():
            body.append(line)
    return body


def test_problem_statement_is_three_lines_and_not_a_ranking():
    body = _section_body(README, "## Problem")
    assert len(body) <= 3
    joined = " ".join(body)
    assert "claimed" in joined
    assert "effective" in joined
    assert "not a ranking" in joined


def test_status_failure_modes_and_version_are_explicit():
    assert "STATUS: WORK-IN-PROGRESS — not A yet" in README
    assert "## FAILURE_MODES" in README
    assert "Magpie" in README
    assert "false green" in README.lower() or "false greens" in README.lower()
    assert "overgeneral" in README.lower()
    assert "Package version: 0.1.0" in README
    assert __version__ == "0.1.0"
    assert f"Offline test functions: {count_test_functions(ROOT / 'tests')}" in README


def test_claims_block_matches_json_recount():
    block = extract_claims_block(README)
    assert block == render_claims(tally_data_dir(ROOT / "data"))
    outside = README.replace(block, "")
    assert "996,354" not in outside
    assert "996354" not in outside


def test_no_machine_local_absolute_paths():
    assert find_absolute_paths(ROOT) == []


def test_check_claims_script_exits_zero():
    proc = subprocess.run(
        [sys.executable, "scripts/check_claims.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_ci_runs_pytest_and_keeps_live_calls_out():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python3 -m pytest" in ci
    assert "scripts/check_claims.py" in ci
    assert "--client mock" in ci
    assert "127.0.0.1:3425" not in ci
