"""Offline fixture path must not call a live endpoint or look like a measurement."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from effective_context_lab.clients import MockClient
from effective_context_lab.probes import NIAHConfig
from effective_context_lab.runner import run_probe

ROOT = Path(__file__).resolve().parents[1]


def test_oracle_mock_scores_the_probe_expected_answer():
    client = MockClient(model="fixture-model", oracle=True, base_url="http://127.0.0.1:9")
    result = run_probe(client, NIAHConfig(seq_len=128, position_frac=0.0, seed=1))
    assert result["score"] == 1.0
    assert result["prediction"] == result["expected"]
    assert result["prompt_tokens"] == 0


def test_blind_mock_is_not_forced_green():
    client = MockClient(model="fixture-model", base_url="http://127.0.0.1:9")
    result = run_probe(client, NIAHConfig(seq_len=128, position_frac=0.0, seed=1))
    assert result["score"] == 0.0
    assert result["prediction"] == "I don't know"


def test_mock_cli_writes_a_labeled_fixture_outside_data(tmp_path):
    env = os.environ.copy()
    env["EFFECTIVE_CONTEXT_API_KEY"] = "super-secret-token"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--client",
            "mock",
            "--oracle",
            "--seq-lens",
            "128",
            "--positions",
            "0.0",
            "--repeats",
            "1",
            "--task",
            "single_needle",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    combined = proc.stdout + proc.stderr
    assert "FIXTURE" in combined
    assert "not a live measurement" in combined
    assert "super-secret-token" not in combined
    written = list(tmp_path.glob("*.json"))
    assert len(written) == 1
    doc = json.loads(written[0].read_text(encoding="utf-8"))
    assert doc["model"] == "fixture-model"
    assert doc["cells"][0]["accuracy"] == 1.0
    assert not list((ROOT / "data").glob("fixture-*.json"))


def test_blind_mock_cli_stays_at_zero(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--client",
            "mock",
            "--seq-lens",
            "128",
            "--positions",
            "0.0",
            "--repeats",
            "1",
            "--task",
            "single_needle",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert doc["cells"][0]["accuracy"] == 0.0
    assert "FIXTURE" in proc.stdout


def test_cli_help_separates_mock_from_the_live_default():
    proc = subprocess.run(
        [sys.executable, "scripts/run_benchmark.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--client" in proc.stdout
    assert "mock" in proc.stdout
    assert "(default: 300)" in proc.stdout
    assert "EFFECTIVE_CONTEXT_API_KEY" in proc.stdout
