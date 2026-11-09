# Effective Context Lab

[![CI](https://github.com/aidless/effective-context-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/effective-context-lab/actions/workflows/ci.yml)

STATUS: WORK-IN-PROGRESS — not A yet.

Package version: 0.1.0

Offline test functions: 60

## Problem

This lab measures the gap between a claimed context window and the effective lengths at which NIAH / RULER-style probes still score as correct.
Committed numbers are one DeepSeek v4.1-flash checkpoint (two gateway model ids), a single-model boundary, not a ranking.
Offline commands recount stored JSON and run a mock fixture; they do not re-call a live 1M endpoint.

## Gaps

This is not A yet:

- Live 1M calls were not re-run here. There is no Magpie or NVIDIA gateway and no API key in this environment. The JSON files are the measurement record.
- Stored scores were not rescored. Cell files have no prediction or expected answer. Result files have a prediction and no expected answer, and their producer script is not in this repo.
- Single-needle prompt tokens for the 1M matrix are UNKNOWN. The claims block says so. A maximum from another file is not the single-needle length.
- Variable tracking is two model ids. The opencode-go file stores `latency_ms=0` on every row.
- The default needle is "the capital of France". A stored 1.0 with the constant prediction Paris does not prove the needle was read.
- RULER v2 has no arXiv id in this repo. Figures cited from the literature notes stay an OBSERVED transcription of those notes.
- `paper/main.pdf` is an earlier compile and was not regenerated after these provenance notes.
- On a live run, claimed context is the `--claimed-context` flag (default 1000000), not a value read from the gateway.

## FAILURE_MODES

### Magpie gateway quirks

- OpenCode Go can return 429 with `Go usage limit exceeded` when the daily quota is gone. The variable-tracking `note` field transcribes that for three missing cells. This repo did not re-check a gateway log.
- `max_tokens=32` leaves reasoning models with empty content and a false zero. The live CLI default is 300, the same as `BenchmarkConfig`. `data/final-benchmark-20261101-175003.json` still has minimum stored accuracy 0.
- `data/glm53-benchmark-20261101-180015.json` and `data/glm53-benchmark-retry-20261101-181241.json` are `volcengine/glm-5.3-flash`, a different model, both with minimum stored accuracy 0. They are not a comparison table.
- Aggregation, multi-doc QA, and three variable-tracking rows use model id `nvidia/deepseek-ai/deepseek-v4.1-flash`, not `opencode-go/deepseek-v4.1-flash`.
- The live client sends no auth header unless `--api-key` or `EFFECTIVE_CONTEXT_API_KEY` is set. The value is not logged.

### Judge and scoring false greens

- `run_probe` always scores with `exact_match`, including multi-choice. `multi_choice_accuracy` also returns 1.0 when the expected string is a substring of the prediction.
- Result files already store `score`. Recounting that field cannot catch a judge that marked a wrong answer correct.
- Several result files have a single distinct prediction on every row. Expected answers are absent, so those 1.0 values are not recomputed.
- A client that reports `prompt_tokens=0` used to be rewritten to the whitespace length. The runner now keeps 0. Whitespace length stays in `actual_len` and is not an API token count.
- Cell files are schema-compatible with `BenchmarkResult.to_dict`. That compatibility is not proof this revision wrote them.

### Single-model overgeneralization

- One family, two gateway ids, files dated 2026-11-01. This is a boundary on that checkpoint, not a ranking, and not a statement about other models or lengths above the measured grid.
- The code threshold is 0.856 (`RULER_THRESHOLD`). Stored accuracy of 1.0 on these grids does not locate a decay point, because no cited cell falls below the threshold.
- The generator's default subject is "the capital of France", and the question asks for that fact directly.

## Offline path

No API key. From a fresh clone:

```bash
python3 -m pip install pytest
python3 -m pytest tests/ -q
python3 scripts/check_claims.py
python3 scripts/run_benchmark.py --client mock --oracle --seq-lens 128 --positions 0.0 --repeats 1 --task single_needle
```

The mock command prints `FIXTURE` and writes under `artifacts/offline/`, not `data/`. `--oracle` returns the probe's expected answer so the pipeline can score a hit. Omit `--oracle` and the mock answers "I don't know" (score 0). Neither result is a measurement.

`matplotlib` and `numpy` in `requirements.txt` are only for `scripts/plot_results.py`. CI installs pytest and does not regenerate `reports/figures/`. Those PNGs are earlier artifacts.

## Live path

Not run in CI. This environment did not call an endpoint. A live run needs an OpenAI-compatible server:

```bash
python3 scripts/run_benchmark.py --client openai \
  --model opencode-go/deepseek-v4.1-flash \
  --base-url http://127.0.0.1:3425/v1 \
  --seq-lens 4096 65536 262144 524288 1000000 \
  --positions 0.0 0.25 0.5 0.75 1.0 \
  --repeats 2 --seed 7 --max-tokens 300 \
  --task single_needle
```

`--seq-lens` and `--positions` are space-separated. A comma-separated list exits 2. Output names include a timestamp and do not overwrite existing `data/` files. A new live file is not part of the claims block until that block is regenerated and reviewed.

Historical result-schema files use `results` and `generated_at`. The current writer emits `cells`. Re-running the command above would not reproduce those JSON documents.

## Claims

The block between the markers is the output of `effective_context_lab.recompute.render_claims` on `data/*.json`. `scripts/check_claims.py` fails if the block, the test-function count, or the package version drifts. Do not hand-edit numbers inside the block.

<!-- CLAIMS:BEGIN -->
Recount of stored score fields in data/*.json. These counts are not rescored: cell files omit the prediction and the expected answer, and result files omit the expected answer.

| file | model | schema | task | rows | cases | fully_correct_cases | stored_score_mass | min | max | prompt_tokens_max | prompt_tokens_at_1m | latency_zero_rows | unique_predictions | provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1m-full-matrix-20261101-185523.json | opencode-go/deepseek-v4.1-flash | cells | single_needle | 25 | 50 | 50 | 50 | 1 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| aggregation-20261101-222254.json | nvidia/deepseek-ai/deepseek-v4.1-flash | results | UNKNOWN | 20 | 20 | 20 | 20 | 1 | 1 | 996364 | 996364 | 0 | 1 | stored_result_score_not_rescored |
| final-benchmark-20261101-175003.json | opencode-go/deepseek-v4.1-flash | cells | single_needle | 30 | 60 | 32 | 45 | 0 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| final-benchmark-fixed-20261101-182756.json | opencode-go/deepseek-v4.1-flash | cells | single_needle | 30 | 60 | 60 | 60 | 1 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| fine-position-benchmark-20261101-174356.json | opencode-go/deepseek-v4.1-flash | cells | single_needle | 20 | 20 | 14 | 14 | 0 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| glm53-benchmark-20261101-180015.json | volcengine/glm-5.3-flash | cells | single_needle | 20 | 40 | 2 | 12 | 0 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| glm53-benchmark-retry-20261101-181241.json | volcengine/glm-5.3-flash | cells | single_needle | 20 | 40 | 12 | 16 | 0 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| multi-choice-20261101-192704.json | opencode-go/deepseek-v4.1-flash | results | UNKNOWN | 25 | 25 | 25 | 25 | 1 | 1 | 996354 | 996353,996354 | 0 | 1 | stored_result_score_not_rescored |
| multi-doc-qa-20261101-225024.json | nvidia/deepseek-ai/deepseek-v4.1-flash | results | UNKNOWN | 20 | 20 | 20 | 20 | 1 | 1 | 996506 | 996506 | 0 | 1 | stored_result_score_not_rescored |
| multi-needle-2-20261101-191936.json | opencode-go/deepseek-v4.1-flash | results | UNKNOWN | 20 | 20 | 20 | 20 | 1 | 1 | 996353 | 996353 | 0 | 1 | stored_result_score_not_rescored |
| opencode-go-deepseek-v4.1-flash-benchmark-20261101-174136.json | opencode-go/deepseek-v4.1-flash | cells | single_needle | 18 | 36 | 28 | 32 | 0.500 | 1 | UNKNOWN | UNKNOWN | 0 | UNKNOWN | stored_cell_accuracy_not_rescored |
| variable-tracking-1m-20261101-215955.json | nvidia/deepseek-ai/deepseek-v4.1-flash | results | UNKNOWN | 3 | 3 | 3 | 3 | 1 | 1 | 996419 | 996419 | 0 | 1 | stored_result_score_not_rescored |
| variable-tracking-20261101-200943.json | opencode-go/deepseek-v4.1-flash | results | UNKNOWN | 22 | 22 | 22 | 22 | 1 | 1 | 996419 | 996419 | 22 | 1 | stored_result_score_not_rescored |

Findings derived from the table above:

- Result-schema files (aggregation-20261101-222254.json, multi-choice-20261101-192704.json, multi-doc-qa-20261101-225024.json, multi-needle-2-20261101-191936.json, variable-tracking-1m-20261101-215955.json, variable-tracking-20261101-200943.json) use `results`/`generated_at` rather than BenchmarkResult.to_dict. The producer script is not in this repo. Stored `score` values are not rescored.
- `1m-full-matrix-20261101-185523.json` does not store prompt_tokens. The single-needle 1M prompt token count is UNKNOWN. Do not copy a prompt_tokens figure from another file onto this one.
- `1m-full-matrix-20261101-185523.json` OBSERVED avg_latency_ms at seq_len=1000000: 22194.019 to 54961.303.
- Variable-tracking rows are split across two model ids: variable-tracking-1m-20261101-215955.json=nvidia/deepseek-ai/deepseek-v4.1-flash (3/3); variable-tracking-20261101-200943.json=opencode-go/deepseek-v4.1-flash (22/22). Key overlap=0. Union rows=25. A combined 25/25 figure is a union of stored scores, not one endpoint.
- `variable-tracking-20261101-200943.json` has latency_zero_rows=22 (every stored latency_ms is 0). Timing was not recorded in this file.
- OBSERVED transcription of `variable-tracking-20261101-200943.json` note field (not re-verified against a gateway log): 22/25 cells (1M pos0.5/0.75/1.0 因 429 配额超限未跑)
- prompt_tokens at seq_len=1000000 in results-schema files only: min=996353 max=996506. The single-needle matrix is excluded because the field is absent.
- `aggregation-20261101-222254.json` sole stored prediction='420' on 20 rows. Expected answers are absent, so this is not a rescore. A constant prediction fits a fixed needle and also fits a score that ignored position.
- `multi-choice-20261101-192704.json` sole stored prediction='Paris' on 25 rows. Expected answers are absent, so this is not a rescore. A constant prediction fits a fixed needle and also fits a score that ignored position.
- `multi-doc-qa-20261101-225024.json` sole stored prediction='value_8_1' on 20 rows. Expected answers are absent, so this is not a rescore. A constant prediction fits a fixed needle and also fits a score that ignored position.
- `multi-needle-2-20261101-191936.json` sole stored prediction='Paris' on 20 rows. Expected answers are absent, so this is not a rescore. A constant prediction fits a fixed needle and also fits a score that ignored position.
- `variable-tracking-1m-20261101-215955.json` sole stored prediction='468' on 3 rows. Expected answers are absent, so this is not a rescore. A constant prediction fits a fixed needle and also fits a score that ignored position.
- `variable-tracking-20261101-200943.json` sole stored prediction='468' on 22 rows. Expected answers are absent, so this is not a rescore. A constant prediction fits a fixed needle and also fits a score that ignored position.
- Cell-schema files are schema-compatible with BenchmarkResult.to_dict. Compatibility is not proof that this revision wrote those files.
<!-- CLAIMS:END -->

## Layout

```
effective_context_lab/   probes, scoring, OpenAI-compatible client, MockClient, runner
scripts/run_benchmark.py live endpoint (--client openai) or offline fixture (--client mock)
scripts/check_claims.py  README drift gate, no network
scripts/plot_results.py  optional figures; variable-tracking input is data/variable-tracking-20*.json
tests/                   offline tests
data/                    committed JSON, including superseded runs
reports/                 earlier writeups; the claims block is the checked tally
paper/main.md            methods and results, with a provenance banner
paper/main.pdf           earlier compile, not regenerated
```

## License

MIT. See `LICENSE`.

RULER v1 is arXiv:2404.06654. This repo does not contain a RULER v2 arXiv id.
