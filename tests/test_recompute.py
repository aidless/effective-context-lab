"""Recount committed JSON. Scores are stored fields, not a rescore."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from effective_context_lab.recompute import (
    tally_document,
    tally_data_dir,
    render_claims,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MATRIX = DATA / "1m-full-matrix-20261101-185523.json"
MULTI_CHOICE = DATA / "multi-choice-20261101-192704.json"
VT = DATA / "variable-tracking-20261101-200943.json"
VT1M = DATA / "variable-tracking-1m-20261101-215955.json"


def _raw_cell_stats(path: Path) -> dict:
    doc = json.loads(path.read_text())
    cells = doc["cells"]
    return {
        "model": doc["model"],
        "rows": len(cells),
        "cases": sum(c["n_cases"] for c in cells),
        "mass": sum(c["accuracy"] * c["n_cases"] for c in cells),
        "fully_correct": sum(c["n_cases"] for c in cells if c["accuracy"] == 1.0),
        "min": min(c["accuracy"] for c in cells),
        "max": max(c["accuracy"] for c in cells),
        "has_prompt_tokens": any("prompt_tokens" in c for c in cells),
    }


def _raw_result_stats(path: Path) -> dict:
    doc = json.loads(path.read_text())
    rows = doc["results"]
    scores = [r["score"] for r in rows]
    return {
        "model": doc["model"],
        "rows": len(rows),
        "mass": sum(scores),
        "fully_correct": sum(1 for s in scores if s == 1.0),
        "min": min(scores),
        "max": max(scores),
        "prompt_max": max(r["prompt_tokens"] for r in rows),
        "preds": {r["prediction"] for r in rows},
        "latency_zero": sum(1 for r in rows if r["latency_ms"] == 0),
    }


def test_cell_tally_matches_raw_json_not_a_hardcoded_score():
    raw = _raw_cell_stats(MATRIX)
    tally = tally_document(json.loads(MATRIX.read_text()), MATRIX.name)
    assert tally.schema == "cells"
    assert tally.model == raw["model"]
    assert tally.n_rows == raw["rows"]
    assert tally.n_cases == raw["cases"]
    assert tally.stored_score_mass == raw["mass"]
    assert tally.fully_correct_cases == raw["fully_correct"]
    assert tally.min_score == raw["min"]
    assert tally.max_score == raw["max"]
    assert raw["has_prompt_tokens"] is False
    assert tally.prompt_tokens_max is None
    assert tally.provenance == "stored_cell_accuracy_not_rescored"


def test_result_tally_matches_raw_json_and_does_not_rescore():
    raw = _raw_result_stats(MULTI_CHOICE)
    tally = tally_document(json.loads(MULTI_CHOICE.read_text()), MULTI_CHOICE.name)
    assert tally.schema == "results"
    assert tally.model == raw["model"]
    assert tally.n_rows == raw["rows"]
    assert tally.n_cases == raw["rows"]
    assert tally.fully_correct_cases == raw["fully_correct"]
    assert tally.prompt_tokens_max == raw["prompt_max"]
    assert tally.unique_predictions == len(raw["preds"])
    assert tally.latency_zero_rows == raw["latency_zero"]
    assert tally.provenance == "stored_result_score_not_rescored"


def test_claims_block_labels_unknown_prompt_tokens_and_split_models():
    tallies = tally_data_dir(DATA)
    text = render_claims(tallies)
    matrix_rows = [
        line for line in text.splitlines() if line.startswith("|") and MATRIX.name in line
    ]
    assert len(matrix_rows) == 1
    assert "UNKNOWN" in matrix_rows[0]
    assert "996354" not in matrix_rows[0]
    assert "996,354" not in matrix_rows[0]

    vt = next(t for t in tallies if t.file == VT.name)
    vt1 = next(t for t in tallies if t.file == VT1M.name)
    assert vt.model != vt1.model
    assert vt.latency_zero_rows == vt.n_rows
    assert "two model ids" in text
    assert "not rescored" in text
    assert "producer_script_not_in_repo" in text or "producer script is not in this repo" in text


def test_data_dir_covers_every_committed_json():
    tallies = tally_data_dir(DATA)
    names = {t.file for t in tallies}
    assert names == {p.name for p in DATA.glob("*.json")}
    assert len(names) == 13


def test_render_is_deterministic_and_uses_relative_names():
    tallies = tally_data_dir(DATA)
    assert render_claims(tallies) == render_claims(tallies)
    rendered = render_claims(tallies)
    for prefix in ("home", "Users", "workspace", "opt"):
        assert f"/{prefix}/" not in rendered
