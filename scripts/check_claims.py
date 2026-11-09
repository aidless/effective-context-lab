#!/usr/bin/env python3
"""Fail when the README claims block drifts from data/*.json.

This recounts stored score fields. It does not rescore model outputs and it
does not call a live endpoint.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from effective_context_lab.recompute import (  # noqa: E402
    count_test_functions,
    extract_claims_block,
    find_absolute_paths,
    render_claims,
    tally_data_dir,
)


def main() -> int:
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    expected = render_claims(tally_data_dir(ROOT / "data"))
    try:
        actual = extract_claims_block(readme)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if actual != expected:
        print("README claims block does not match the data/*.json recount.", file=sys.stderr)
        print("--- recount ---", file=sys.stderr)
        print(expected, file=sys.stderr)
        print("--- readme block ---", file=sys.stderr)
        print(actual, file=sys.stderr)
        return 1

    test_count = count_test_functions(ROOT / "tests")
    needle = f"Offline test functions: {test_count}"
    if needle not in readme:
        print(f"README is missing {needle!r}.", file=sys.stderr)
        return 1

    version_path = ROOT / "effective_context_lab" / "__init__.py"
    version_text = version_path.read_text(encoding="utf-8")
    if '__version__ = "0.1.0"' not in version_text:
        print("Package version is no longer 0.1.0. Keep VERSION honest.", file=sys.stderr)
        return 1
    if "Package version: 0.1.0" not in readme:
        print("README package version line does not match 0.1.0.", file=sys.stderr)
        return 1

    hits = find_absolute_paths(ROOT)
    if hits:
        print("Machine-local absolute paths:", file=sys.stderr)
        print("\n".join(hits), file=sys.stderr)
        return 1

    print(f"claims ok: README block matches data/*.json; {needle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
