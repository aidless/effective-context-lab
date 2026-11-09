"""Recount stored scores in committed benchmark JSON.

Nothing in this module rescores a model completion. Cell files store an
accuracy mean and do not store the prediction or the expected answer.
Result files store a score and a prediction, and do not store the expected
answer. A tally is a sum over those stored fields.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

CLAIMS_BEGIN = "<!-- CLAIMS:BEGIN -->"
CLAIMS_END = "<!-- CLAIMS:END -->"
_ABS_PATH = re.compile(
    r"(?<![\w:])/(?:home|Users)/[A-Za-z0-9._-]+"
    r"|(?<![\w:])/(?:workspace|opt)/[A-Za-z0-9._-]+"
)
_SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", "artifacts", ".venv", "venv"}
_SKIP_SUFFIXES = {".png", ".pdf", ".pyc", ".pyo"}


@dataclass(frozen=True)
class FileTally:
    """One committed JSON file, counted from stored fields."""

    file: str
    model: str
    schema: str
    task: str
    n_rows: int
    n_cases: int
    fully_correct_cases: float
    stored_score_mass: float
    min_score: float | None
    max_score: float | None
    prompt_tokens_max: int | None
    prompt_tokens_1m: tuple[int, ...] | None
    latency_zero_rows: int | None
    latency_1m_min_ms: float | None
    latency_1m_max_ms: float | None
    unique_predictions: int | None
    sole_prediction: str | None
    row_keys: tuple[tuple[int, float], ...]
    note: str | None
    provenance: str


def tally_document(doc: dict, file: str) -> FileTally:
    """Tally one parsed JSON document.

    ``file`` is the repository-relative file name, not an absolute path.
    """
    model = str(doc.get("model", "UNKNOWN"))
    note = None if doc.get("note") is None else str(doc.get("note"))
    if "cells" in doc:
        return _tally_cells(doc, file, model, note)
    if "results" in doc:
        return _tally_results(doc, file, model, note)
    return FileTally(
        file=file,
        model=model,
        schema="unknown",
        task="UNKNOWN",
        n_rows=0,
        n_cases=0,
        fully_correct_cases=0,
        stored_score_mass=0.0,
        min_score=None,
        max_score=None,
        prompt_tokens_max=None,
        prompt_tokens_1m=None,
        latency_zero_rows=None,
        latency_1m_min_ms=None,
        latency_1m_max_ms=None,
        unique_predictions=None,
        sole_prediction=None,
        row_keys=(),
        note=note,
        provenance="unrecognized_schema",
    )


def tally_data_dir(data_dir: Path) -> list[FileTally]:
    """Tally every ``*.json`` file in ``data_dir``, sorted by file name."""
    tallies: list[FileTally] = []
    for path in sorted(Path(data_dir).glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        tallies.append(tally_document(doc, path.name))
    return tallies


def extract_claims_block(readme: str) -> str:
    """Return the README claims block, excluding the marker lines."""
    start = readme.find(CLAIMS_BEGIN)
    end = readme.find(CLAIMS_END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(
            "README is missing the claims markers "
            f"{CLAIMS_BEGIN} ... {CLAIMS_END}"
        )
    body = readme[start + len(CLAIMS_BEGIN) : end]
    if body.startswith("\n"):
        body = body[1:]
    if not body.endswith("\n"):
        body += "\n"
    return body


def count_test_functions(tests_dir: Path) -> int:
    """Count ``test_*`` functions defined in ``tests/test_*.py``."""
    total = 0
    for path in sorted(Path(tests_dir).glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        total += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    return total


def find_absolute_paths(root: Path) -> list[str]:
    """Return ``path:line`` hits for machine-local absolute paths."""
    hits: list[str] = []
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if _ABS_PATH.search(line):
                hits.append(f"{path.relative_to(root)}:{line_no}")
    return hits


def render_claims(tallies: list[FileTally]) -> str:
    """Render the drift-checked claims block. No absolute paths."""
    lines = [
        "Recount of stored score fields in data/*.json. "
        "These counts are not rescored: cell files omit the prediction and the expected answer, "
        "and result files omit the expected answer.",
        "",
        "| file | model | schema | task | rows | cases | fully_correct_cases | stored_score_mass | min | max | prompt_tokens_max | prompt_tokens_at_1m | latency_zero_rows | unique_predictions | provenance |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tally in tallies:
        lines.append(
            "| "
            + " | ".join(
                [
                    tally.file,
                    tally.model,
                    tally.schema,
                    tally.task,
                    _num(tally.n_rows),
                    _num(tally.n_cases),
                    _num(tally.fully_correct_cases),
                    _num(tally.stored_score_mass),
                    _num(tally.min_score),
                    _num(tally.max_score),
                    _num(tally.prompt_tokens_max),
                    _fmt_token_set(tally.prompt_tokens_1m),
                    _num(tally.latency_zero_rows),
                    _num(tally.unique_predictions),
                    tally.provenance,
                ]
            )
            + " |"
        )
    lines.append("")
    lines.extend(_findings(tallies))
    return "\n".join(lines) + "\n"


def _tally_cells(doc: dict, file: str, model: str, note: str | None) -> FileTally:
    cells = doc["cells"]
    task = str(doc.get("config", {}).get("task", "UNKNOWN"))
    accuracies = [float(cell["accuracy"]) for cell in cells]
    n_cases = sum(int(cell["n_cases"]) for cell in cells)
    mass = sum(float(cell["accuracy"]) * int(cell["n_cases"]) for cell in cells)
    fully = sum(int(cell["n_cases"]) for cell in cells if float(cell["accuracy"]) == 1.0)
    keys = tuple((int(cell["seq_len"]), float(cell["position_frac"])) for cell in cells)
    lats_1m = [
        float(cell["avg_latency_ms"])
        for cell in cells
        if int(cell["seq_len"]) == 1_000_000 and "avg_latency_ms" in cell
    ]
    zero = sum(1 for cell in cells if float(cell.get("avg_latency_ms", -1)) == 0.0)
    return FileTally(
        file=file,
        model=model,
        schema="cells",
        task=task,
        n_rows=len(cells),
        n_cases=n_cases,
        fully_correct_cases=fully,
        stored_score_mass=mass,
        min_score=min(accuracies) if accuracies else None,
        max_score=max(accuracies) if accuracies else None,
        prompt_tokens_max=None,
        prompt_tokens_1m=None,
        latency_zero_rows=zero,
        latency_1m_min_ms=min(lats_1m) if lats_1m else None,
        latency_1m_max_ms=max(lats_1m) if lats_1m else None,
        unique_predictions=None,
        sole_prediction=None,
        row_keys=keys,
        note=note,
        provenance="stored_cell_accuracy_not_rescored",
    )


def _tally_results(doc: dict, file: str, model: str, note: str | None) -> FileTally:
    rows = doc["results"]
    scores = [float(row["score"]) for row in rows]
    prompts = [int(row["prompt_tokens"]) for row in rows if "prompt_tokens" in row]
    prompts_1m = tuple(
        sorted(
            {
                int(row["prompt_tokens"])
                for row in rows
                if int(row.get("seq_len", -1)) == 1_000_000 and "prompt_tokens" in row
            }
        )
    )
    preds = [str(row["prediction"]) for row in rows if "prediction" in row]
    unique = len(set(preds)) if preds else None
    sole = preds[0] if unique == 1 else None
    keys = tuple((int(row["seq_len"]), float(row["position_frac"])) for row in rows)
    lats_1m = [
        float(row["latency_ms"])
        for row in rows
        if int(row.get("seq_len", -1)) == 1_000_000 and "latency_ms" in row
    ]
    zero = (
        sum(1 for row in rows if float(row.get("latency_ms", -1)) == 0.0)
        if rows and "latency_ms" in rows[0]
        else None
    )
    return FileTally(
        file=file,
        model=model,
        schema="results",
        task="UNKNOWN",
        n_rows=len(rows),
        n_cases=len(rows),
        fully_correct_cases=sum(1 for score in scores if score == 1.0),
        stored_score_mass=sum(scores),
        min_score=min(scores) if scores else None,
        max_score=max(scores) if scores else None,
        prompt_tokens_max=max(prompts) if prompts else None,
        prompt_tokens_1m=prompts_1m if prompts_1m else None,
        latency_zero_rows=zero,
        latency_1m_min_ms=min(lats_1m) if lats_1m else None,
        latency_1m_max_ms=max(lats_1m) if lats_1m else None,
        unique_predictions=unique,
        sole_prediction=sole,
        row_keys=keys,
        note=note,
        provenance="stored_result_score_not_rescored",
    )


def _findings(tallies: list[FileTally]) -> list[str]:
    lines = ["Findings derived from the table above:", ""]
    result_files = [tally for tally in tallies if tally.schema == "results"]
    if result_files:
        names = ", ".join(tally.file for tally in result_files)
        lines.append(
            f"- Result-schema files ({names}) use `results`/`generated_at` rather than "
            "BenchmarkResult.to_dict. The producer script is not in this repo. "
            "Stored `score` values are not rescored."
        )
    matrix = next((tally for tally in tallies if tally.file.startswith("1m-full-matrix")), None)
    if matrix is not None and matrix.prompt_tokens_max is None:
        lines.append(
            f"- `{matrix.file}` does not store prompt_tokens. "
            "The single-needle 1M prompt token count is UNKNOWN. "
            "Do not copy a prompt_tokens figure from another file onto this one."
        )
        if matrix.latency_1m_min_ms is not None and matrix.latency_1m_max_ms is not None:
            lines.append(
                f"- `{matrix.file}` OBSERVED avg_latency_ms at seq_len=1000000: "
                f"{matrix.latency_1m_min_ms:.3f} to {matrix.latency_1m_max_ms:.3f}."
            )
    tracking = [tally for tally in tallies if tally.file.startswith("variable-tracking")]
    if len(tracking) >= 2 and len({tally.model for tally in tracking}) > 1:
        parts = [
            f"{tally.file}={tally.model} ({_num(tally.fully_correct_cases)}/{_num(tally.n_cases)})"
            for tally in tracking
        ]
        key_sets = [set(tally.row_keys) for tally in tracking]
        overlap = set.intersection(*key_sets)
        union = set.union(*key_sets)
        lines.append(
            "- Variable-tracking rows are split across two model ids: "
            + "; ".join(parts)
            + f". Key overlap={len(overlap)}. Union rows={len(union)}. "
            "A combined 25/25 figure is a union of stored scores, not one endpoint."
        )
    for tally in tracking:
        if tally.n_rows and tally.latency_zero_rows == tally.n_rows:
            lines.append(
                f"- `{tally.file}` has latency_zero_rows={tally.latency_zero_rows} "
                "(every stored latency_ms is 0). Timing was not recorded in this file."
            )
        if tally.note:
            lines.append(
                f"- OBSERVED transcription of `{tally.file}` note field "
                f"(not re-verified against a gateway log): {tally.note}"
            )
    one_m_tokens: list[int] = []
    for tally in tallies:
        if tally.prompt_tokens_1m:
            one_m_tokens.extend(tally.prompt_tokens_1m)
    if one_m_tokens:
        lines.append(
            "- prompt_tokens at seq_len=1000000 in results-schema files only: "
            f"min={min(one_m_tokens)} max={max(one_m_tokens)}. "
            "The single-needle matrix is excluded because the field is absent."
        )
    for tally in tallies:
        if tally.sole_prediction is None:
            continue
        lines.append(
            f"- `{tally.file}` sole stored prediction={tally.sole_prediction!r} "
            f"on {tally.n_rows} rows. Expected answers are absent, so this is not a rescore. "
            "A constant prediction fits a fixed needle and also fits a score that ignored position."
        )
    lines.append(
        "- Cell-schema files are schema-compatible with BenchmarkResult.to_dict. "
        "Compatibility is not proof that this revision wrote those files."
    )
    return lines


def _num(value: float | int | None) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _fmt_token_set(values: tuple[int, ...] | None) -> str:
    if not values:
        return "UNKNOWN"
    return ",".join(str(value) for value in values)
