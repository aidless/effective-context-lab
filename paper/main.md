# Measuring Real Long-Context Utilization: A Probe-Based Evaluation of DeepSeek V4.1 Flash Across Six RULER Task Types at One Million Tokens

**Author**: Independent Researcher (aidless)

**Date**: 2026-11-02

---

## Abstract

Long-context language models advertise context windows of up to one million tokens. Yet their *effective* usable context often falls far short of the advertised size. Prior benchmarks (RULER, BABILong, ∞Bench) showed that most models utilize only 10-20% of their advertised context on reasoning tasks.

We measure the effective context utilization of DeepSeek V4.1 Flash (a state-of-the-art reasoning model). We use controlled Needle-In-A-Haystack (NIAH) probes across all six RULER task types, at varying lengths (65K to 1M tokens) and positions (0.0 to 1.0).

Contrary to the decay pattern in prior benchmarks, DeepSeek V4.1 Flash maintains perfect accuracy (100%) across all six task types and all positions within its advertised 1M-token window. The true context reaches 996K tokens (99.6% of advertised).

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
2. **Context length via `prompt_tokens`**: We use the API-reported `prompt_tokens` for context length, not whitespace-based tokenization (which underestimates by ~1.26× due to tokenizer expansion). A 1M-token probe reaches `prompt_tokens=996,354` (99.6% of advertised).

---

## 4. Results

### 4.1 Context Length Verification

| Target seq_len | Actual prompt_tokens | Ratio |
|---------------|---------------------|-------|
| 65,536 | 65,363-65,515 | ~0.998 |
| 262,144 | 261,228-261,380 | ~0.996 |
| 524,288 | 522,406-522,559 | ~0.996 |
| 1,000,000 | 996,353-996,506 | ~0.996 |

The advertised 1M window is reached at 99.6% (996K tokens), confirming the model truly processes near-1M context.

### 4.2 Accuracy Across All Six Task Types

| Task | Lengths tested | Positions | Accuracy | Cells |
|------|---------------|-----------|----------|-------|
| Single-Needle NIAH | 4K-1M | 0.0-1.0 | **1.00** | 25/25 |
| Multi-Needle (2) | 65K-1M | 0.0-1.0 | **1.00** | 20/20 |
| Multi-Choice | 4K-1M | 0.0-1.0 | **1.00** | 25/25 |
| Variable Tracking | 4K-1M | 0.0-1.0 | **1.00** | 25/25 |
| Aggregation | 65K-1M | 0.0-1.0 | **1.00** | 20/20 |
| Multi-doc QA | 65K-1M | 0.0-1.0 | **1.00** | 20/20 |

**All 6 task types achieve 100% accuracy at all positions within the advertised 1M window.** No effective-context decay is observed.

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
| **Ours (2026)** | **1M** | **996K, 100% accuracy** | **No decay observed** |

### 5.2 Why the Difference?

1. **Model**: DeepSeek V4.1 Flash is a frontier reasoning model, possibly among the strongest for long context. Prior benchmarks tested models available at their time (GPT-3.5, LLaMA 2, etc.), which are weaker.
2. **Task complexity**: We test all six RULER task types including cross-context reasoning (aggregation, multi-doc QA). The model handles all at 1M.
3. **Methodological rigor**: We fix `max_tokens` (32→300) and use `prompt_tokens` for context length. Prior benchmarks may have underestimated performance due to these artifacts.

### 5.3 Limitations

1. **Single provider route**: We used two provider routes for the same model (same weights). Cross-provider consistency not fully tested.
2. **n=1 for complex tasks**: Each cell tested once. Repeats would strengthen confidence.
3. **No >1M testing**: The advertised window is the ceiling. The model may sustain beyond 1M (untested).
4. **Synthetic context**: NIAH uses synthetic haystacks. Real-world context (code, documents) may behave differently (cf. Logic Haystacks).
5. **API gateway**: The Magpie gateway may add noise, though prompt_tokens confirms near-1M processing.

---

## 6. Conclusion

We measured the effective context utilization of DeepSeek V4.1 Flash across all six RULER task types at up to 1M tokens. Contrary to the decay pattern reported in prior benchmarks, **the model maintains perfect accuracy (100%) across all task types and positions within its advertised 1M window**, with true context reaching 996K tokens. This suggests that frontier reasoning models may have substantially higher effective context utilization than earlier models, and that careful methodology (proper output budget, accurate token accounting, full task-complexity spectrum) is essential for valid long-context evaluation.

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
