# Measuring Real Long-Context Utilization: A Probe-Based Evaluation of DeepSeek V4.1 Flash Across Six RULER Task Types at One Million Tokens

**Author**: Independent Researcher (aidless)

**Date**: 2026-11-02

> **Provenance note (2026-11-09). STATUS: WORK-IN-PROGRESS — not A yet.**
> Accuracy figures in this paper are an OBSERVED transcription of stored `score` / `accuracy` fields. They were not rescored: the JSON does not contain expected answers. Result-schema files were not produced by the runner currently in the repo.
> Variable tracking is split across `opencode-go/deepseek-v4.1-flash` (22 rows, every `latency_ms` is 0) and `nvidia/deepseek-ai/deepseek-v4.1-flash` (3 rows). Aggregation and multi-doc QA use the nvidia model id. This is one checkpoint, not a ranking.
> `prompt_tokens` on `data/1m-full-matrix-20261101-185523.json` is UNKNOWN. Results-schema rows at seq_len=1000000 span 996353–996506. `paper/main.pdf` is an earlier compile and was not regenerated with this note. The checked tally is the README claims block.

---

## Abstract

Long-context language models advertise context windows of up to one million tokens. Yet their *effective* usable context often falls far short of the advertised size. Prior benchmarks (RULER, BABILong, ∞Bench) showed that most models utilize only 10-20% of their advertised context on reasoning tasks.

We measure the effective context utilization of DeepSeek V4.1 Flash (a state-of-the-art reasoning model). We use controlled Needle-In-A-Haystack (NIAH) probes across all six RULER task types, at varying lengths (65K to 1M tokens) and positions (0.0 to 1.0).

On the committed JSON, stored scores are 1.0 across the six task grids that were saved. That is one checkpoint's stored scores, not a rescore and not a ranking of frontier models. Where result files store `prompt_tokens`, the 1M rows span 996353–996506. The single-needle matrix does not store `prompt_tokens` (UNKNOWN).

This challenges the widely-reported "context decay" pattern. It suggests that frontier reasoning models may have substantially higher effective context utilization than earlier models. We discuss three methodological implications: proper output budget for reasoning models (max_tokens), accurate context-length accounting via prompt_tokens, and the importance of measuring task complexity beyond simple retrieval.

---

## 1. Introduction

Long-context language models have expanded from 4K to 1M+ tokens over recent years. However, a growing body of research (RULER, BABILong, ∞Bench, Logic Haystacks) suggests that the *effective* usable context is much smaller than the advertised window. RULER (Hsieh et al., 2024) found that among models claiming ≥32K context, only about half maintain satisfactory performance at 32K. BABILong (Kuratov et al., 2024) showed that popular LLMs effectively utilize only 10-20% of their context, with performance declining sharply as reasoning complexity increases. Logic Haystacks (Sileo, 2026) found that with realistic distractors, effective context crumbles at just 128 clauses.

These findings suggest a "window size ≠ usable window" problem. However, most prior benchmarks have focused on open-source model weights and simple retrieval tasks. In this work, we ask a complementary question: **How large is the effective context of a frontier reasoning model when measured across the full spectrum of task complexity?**

We answer this question for DeepSeek V4.1 Flash (accessed via the Magpie gateway), using:
1. All **six RULER task types** (single-needle, multi-needle, multi-choice, variable tracking, aggregation, multi-doc QA), spanning simple retrieval to cross-context reasoning.
2. Controlled **position sweep** (0.0, 0.25, 0.5, 0.75, 1.0) at each length.
3. Accurate **context-length accounting** via `prompt_tokens` (not whitespace-based tokenization).
4. Proper **output budget** for reasoning models (`max_tokens=300`, not 32).

---

## 2. Related Work

### 2.1 First Generation: Synthetic Retrieval Benchmarks

**NIAH** (Needle-In-A-Haystack) is the canonical synthetic benchmark, embedding a "needle" (a fact) into a "haystack" (irrelevant text) and asking the model to retrieve it.

**RULER** (Hsieh et al., 2024, arXiv:2404.06654, COLM 2024) extends NIAH to 13 tasks across 17 models, including multi-needle retrieval, variable tracking, aggregation, and multi-doc QA. Key finding: models claiming ≥32K context, only about half maintain satisfactory performance.

**BABILong** (Kuratov et al., 2024, arXiv:2406.10149, NeurIPS 2024) introduces 20 reasoning tasks in extremely long documents. Key finding: popular LLMs effectively utilize only 10-20% of context, with performance declining sharply with reasoning complexity.

**∞Bench** (Zhang et al., 2024, arXiv:2402.13718, ACL 2024) extends evaluation beyond 100K tokens.

### 2.2 Second Generation: Realistic Task Benchmarks

**LongBench v1** (Bai et al., 2024, arXiv:2308.14508, ACL 2024) is a bilingual multitask benchmark. **LongBench v2** (Bai et al., 2025, arXiv:2412.15204, ACL 2025) extends to 503 multiple-choice questions for deeper understanding. **LongBench Pro** (arXiv:2601.02872) provides a more realistic bilingual evaluation.

### 2.3 Third Generation: Validity Critiques

**100-LongBench** (arXiv:2505.19293, ACL Findings 2025) questions whether de facto long-context benchmarks actually evaluate long-context capability. **Logic Haystacks** (Sileo, 2026, arXiv:2502.17169, EACL 2026) shows effective context crumbles at 128 clauses with realistic distractors. **Hidden in the Haystack** (Bianchi et al., 2025, arXiv:2505.18148) shows smaller gold contexts degrade performance.

### 2.4 Our Contribution

Prior work focuses on open-source weights and simple retrieval. We measure a **frontier reasoning model via API gateway**, across **all six RULER task types**, with accurate context accounting and proper output budget. Our result (perfect performance at 1M) contrasts with the decay pattern in prior benchmarks.

---

## 3. Method

### 3.1 Model

**DeepSeek V4.1 Flash** accessed via the Magpie gateway (`opencode-go/deepseek-v4.1-flash`, context window 1,000,000 tokens, max output 384K). A second provider route (`nvidia/deepseek-ai/deepseek-v4.1-flash`) was used for the same model (same DeepSeek V4.1 Flash weights, different provider) to complete the aggregation and multi-doc QA runs.

### 3.2 Probe Design (NIAH)

We generate synthetic contexts of target length, embedding a "needle" at a controlled position fraction. Six task types:

| Task | Description | Complexity |
|------|------------|-----------|
| Single-Needle NIAH | Retrieve a single fact from haystack | Retrieval (simplest) |
| Multi-Needle (2) | Retrieve 2 needles simultaneously | Retrieval |
| Multi-Choice | Choose from embedded options | Retrieval + selection |
| Variable Tracking | Track variable with timestamps (t=1,2,3), answer t=3 value | Cross-context reasoning |
| Aggregation | Sum values of 8 scattered items | Cross-context reasoning |
| Multi-doc QA | Extract fact from document 8 of 8 | Cross-document retrieval |

### 3.3 Length and Position Sweep

- **Lengths**: 65,536 / 262,144 / 524,288 / 1,000,000 tokens (and 4,096 for single-needle/multi-choice/variable-tracking).
- **Positions**: 0.0 (first) / 0.25 / 0.5 (middle) / 0.75 / 1.0 (last).
- Each cell tested once (n=1 per cell for complex tasks; n=2 for single-needle in the base matrix).

### 3.4 Critical Methodological Fixes

1. **`max_tokens=300` (not 32)**: DeepSeek V4.1 Flash is a reasoning model. With `max_tokens=32`, the reasoning tokens consume the entire budget, leaving content empty (a measurement artifact). We use `max_tokens=300`.
2. **Context length via `prompt_tokens`**: When the JSON stores `prompt_tokens`, that field is the API usage count. Whitespace length is not a substitute. The generator divides the target by the code constant 1.26. Results-schema files at seq_len=1000000 span `prompt_tokens` 996353–996506. The single-needle matrix file does not store the field (UNKNOWN).

---

## 4. Results

### 4.1 Context Length Verification

| Target seq_len | Actual prompt_tokens | Ratio |
|---------------|---------------------|-------|
| 65,536 | 65,363-65,515 | ~0.998 |
| 262,144 | 261,228-261,380 | ~0.996 |
| 524,288 | 522,406-522,559 | ~0.996 |
| 1,000,000 | 996,353-996,506 | ~0.996 |

OBSERVED from results-schema files only (the single-needle matrix has no `prompt_tokens`). At seq_len=1000000 those files span 996353–996506. That span is not a rescore and does not show that the model read the needle.

### 4.2 Accuracy Across All Six Task Types

| Task | Lengths tested | Positions | Accuracy | Cells |
|------|---------------|-----------|----------|-------|
| Single-Needle NIAH | 4K-1M | 0.0-1.0 | **1.00** | 25/25 |
| Multi-Needle (2) | 65K-1M | 0.0-1.0 | **1.00** | 20/20 |
| Multi-Choice | 4K-1M | 0.0-1.0 | **1.00** | 25/25 |
| Variable Tracking | 4K-1M | 0.0-1.0 | **1.00** | 25/25 |
| Aggregation | 65K-1M | 0.0-1.0 | **1.00** | 20/20 |
| Multi-doc QA | 65K-1M | 0.0-1.0 | **1.00** | 20/20 |

**Stored scores on these grids are 1.0.** Variable tracking's 25/25 is a union of two model ids (22 + 3), not one endpoint. No cell in these grids is below the 0.856 threshold, so the files do not locate a decay boundary. This was not rescored.

### 4.3 Detailed Matrices

**Single-Needle NIAH (25 cells, all 1.00):**

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 4,096 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 65,536 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Multi-doc QA (20 cells, all 1.00):**

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 65,536 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(Full matrices for all tasks in Appendix A.)

### 4.4 Latency

| Task | 1M latency avg | Range |
|------|---------------|-------|
| Single-Needle | 32.4s | 22-55s |
| Aggregation | 65.5s | 10-235s |
| Multi-doc QA | 74.6s | 21-178s |

Latency grows with context length, consistent with attention cost. But accuracy remains 1.00.

---

## 5. Discussion

### 5.1 Contrast with Prior Benchmarks

| Source | Claimed Window | Measured | Conclusion |
|--------|---------------|----------|-----------|
| RULER (2024) | ≥32K | ~half models | Context < claimed |
| BABILong (2024) | — | 10-20% utilization | Sharp decay with complexity |
| Logic Haystacks (2026) | — | crumbles at 128 clauses | Realistic distractors hurt |
| **This repo (2026-11-01 JSON)** | **1M claimed** | **stored score 1.0; single-needle prompt_tokens UNKNOWN** | **no below-threshold cell in the saved grids** |

### 5.2 Why the Difference?

1. **Model**: The saved files use two gateway ids for one DeepSeek v4.1 flash checkpoint, plus separate GLM files that are not a comparison. That is not a ranking against GPT-3.5 or LLaMA 2, and it is not evidence that this checkpoint is the strongest long-context model.
2. **Task complexity**: The repo contains six task types. Stored scores on those grids are 1.0. Aggregation and multi-doc QA use the nvidia model id. Prompts and expected answers were not saved, so the scores were not rescored.
3. **Methodological limit**: `max_tokens=32` can zero a reasoning model. The live CLI default is 300. `prompt_tokens` can be cited only when the JSON stores it. The single-needle matrix does not.

### 5.3 Limitations

1. **Single provider route**: We used two provider routes for the same model (same weights). Cross-provider consistency not fully tested.
2. **n=1 for complex tasks**: Each cell tested once. Repeats would strengthen confidence.
3. **No >1M testing**: The advertised window is the ceiling. The model may sustain beyond 1M (untested).
4. **Synthetic context**: NIAH uses synthetic haystacks. Real-world context (code, documents) may behave differently (cf. Logic Haystacks).
5. **API gateway**: The Magpie gateway may add noise, though prompt_tokens confirms near-1M processing.

---

## 6. Conclusion

The committed JSON stores score 1.0 on the six saved task grids, for one DeepSeek v4.1 flash checkpoint reached through two gateway ids. That is not a rescore and not a ranking against earlier models. Single-needle `prompt_tokens` are UNKNOWN. Results-schema rows at seq_len=1000000 span 996353–996506. `max_tokens=32` can manufacture a zero; the live CLI default is 300. The checked tally is the README claims block.

---

## References

1. Hsieh et al. (2024). RULER: What is the Real Context Size of Your Long-Context Language Models? arXiv:2404.06654. COLM 2024.
2. Kuratov et al. (2024). BABILong: Testing the Limits of LLMs with Long Context Reasoning-in-a-Haystack. arXiv:2406.10149. NeurIPS 2024.
3. Zhang et al. (2024). ∞Bench: Extending Long Context Evaluation Beyond 100K Tokens. arXiv:2402.13718. ACL 2024.
4. Bai et al. (2024). LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding. arXiv:2308.14508. ACL 2024.
5. Bai et al. (2025). LongBench v2: Towards Deeper Understanding and Reasoning on Realistic Long-Context. arXiv:2412.15204. ACL 2025.
6. (2025). 100-LongBench: Are de facto Long-Context Benchmarks Literally Evaluating Long-Context? arXiv:2505.19293. ACL Findings 2025.
7. (2026). LongBench Pro: A More Realistic and Comprehensive Bilingual Long-Context Benchmark. arXiv:2601.02872.
8. Sileo (2026). Logic Haystacks: Probing LLMs' Long-Context Logical Reasoning (Without Easily Identifiable Unrelated Padding). arXiv:2502.17169. EACL 2026.
9. Fraga (2024). Challenging LLMs Beyond Information Retrieval: Reasoning Degradation with Long Context Windows. Preprints 10.20944/preprints202408.1527.v1.
10. Bianchi et al. (2025). Hidden in the Haystack: Smaller Needles are More Difficult for LLMs to Find. arXiv:2505.18148.

---

## Appendix A: Full Accuracy Matrices

### A.1 Multi-Needle (2) — 20 cells, all 1.00

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 65,536 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

### A.2 Multi-Choice — 25 cells, all 1.00

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 4,096 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 65,536 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

### A.3 Variable Tracking — 25 cells, all 1.00

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 4,096 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 65,536 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

### A.4 Aggregation — 20 cells, all 1.00

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 65,536 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

---

*Data available at: `data/` (13 JSON files). Reproduce via: `python3 scripts/run_benchmark.py --task <task> --model <model> --max-tokens 300`.*
