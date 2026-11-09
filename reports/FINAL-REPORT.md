# 长上下文有效利用率测量报告（修正版）

> **Provenance (2026-11-09). STATUS: WORK-IN-PROGRESS — not A yet.**
> Stored accuracy cells below are an OBSERVED transcription of `accuracy` / `score` in `data/*.json`. They are not a rescore: expected answers are not in those files.
> `prompt_tokens` for `data/1m-full-matrix-20261101-185523.json` is **UNKNOWN** (field absent). Do not read a token count from another file as the single-needle length.
> OBSERVED `avg_latency_ms` at seq_len=1000000 in that file is 22194.019 to 54961.303. Earlier "5-28s" wording does not match the file.
> Variable tracking is two model ids (22 rows `opencode-go/deepseek-v4.1-flash` with every `latency_ms` 0, plus 3 rows `nvidia/deepseek-ai/deepseek-v4.1-flash`). Aggregation and multi-doc QA use the nvidia id. The checked tally is the README claims block.

**测量对象**: `opencode-go/deepseek-v4.1-flash`（Magpie 网关, 声称 1,000,000 tokens 上下文窗口）
**测量方法**: NIAH（Needle In A Haystack）式单针探针
**测量时间**: 2026-11-01（修正版, max_tokens=300）
**关键修正**: 初版用 `max_tokens=32` 低估了 reasoning 模型（DeepSeek 也是 reasoning 模型，32 token 预算全被 reasoning 占满 → content 为空 → 伪影 0）。修正为 `max_tokens=300` 后，所有数据重新测量。

---

## 一、核心结论

> **在修正后的测量下，`deepseek-v4.1-flash` 在真实 1M 上下文窗口内，所有位置（最前/中间/最末）都能正确检索单针信息。**
>
> 具体：131K 完整矩阵（30 cells）**全部 1.00**；262K/524K/1M 各 5 位置**全部 1.00**。
> Single-needle `prompt_tokens` are UNKNOWN on `data/1m-full-matrix-20261101-185523.json`. Stored accuracy on that file is 50/50 cases (25 cells × n_cases 2, every stored accuracy 1).

**这挑战了初版「有效窗口仅 1.6%-13.1%」的结论**——那个结论是 `max_tokens=32` 的测量伪影，不是模型真实能力。

## 二、准确率矩阵（修正后, max_tokens=300, n=2 重复/格）

| seq_len | 0.0 (最前) | 0.25 | 0.5 (中间) | 0.75 | 1.0 (最末) |
|---------|-----------|------|-----------|------|-----------|
| 4,096   | 1.00      | 1.00 | 1.00      | 1.00 | 1.00      |
| 8,192   | 1.00      | 1.00 | 1.00      | 1.00 | 1.00      |
| 16,384  | 1.00      | 1.00 | 1.00      | 1.00 | 1.00      |
| 32,768  | 1.00      | 1.00 | 1.00      | 1.00 | 1.00      |
| 65,536  | 1.00      | 1.00 | 1.00      | 1.00 | 1.00      |
| 131,072 | 1.00      | 1.00 | 1.00      | 1.00 | 1.00      |

## 三、深度扩展（max_tokens=300）

| seq_len | 位置覆盖 | 全部得分 | prompt_tokens | avg_latency_ms (OBSERVED in the 1M matrix file) |
|---------|---------|---------|-------------------|------------------------------------------------|
| 262,144 | 5 位置全测 | 全部 1.00 | UNKNOWN | 6640.930 to 10908.586 |
| 524,288 | 5 位置全测 | 全部 1.00 | UNKNOWN | 14658.471 to 33676.511 |
| 1,000,000 | 5 位置全测 | 全部 1.00 | UNKNOWN | 22194.019 to 54961.303 |

## 三b、1M 完整矩阵确认（25 cells, 2 重复/格 = 50 次测量）

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 4,096   | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 65,536  | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**25 cells 全部 stored accuracy 1.00（2 重复/格 = 50 cases）** in `data/1m-full-matrix-20261101-185523.json`. `prompt_tokens` and `finish_reason` are UNKNOWN in that file.

## 四、有效窗口汇总（修正后）

| 针位置 | 有效窗口 (tokens) | 声称窗口 | 效率比 |
|--------|------------------|---------|--------|
| 0.0 (最前) | 1000000 (max probed seq_len with stored accuracy 1) | 1000000 (flag, not read from the gateway) | prompt_tokens ratio UNKNOWN |
| 0.5 (中间) | 1000000 (max probed seq_len with stored accuracy 1) | 1000000 (flag, not read from the gateway) | prompt_tokens ratio UNKNOWN |
| 1.0 (最末) | 1000000 (max probed seq_len with stored accuracy 1) | 1000000 (flag, not read from the gateway) | prompt_tokens ratio UNKNOWN |

> 注：1M 是测量上限（声称窗口）。实际有效窗口可能 >1M，但当前测量未覆盖 >1M。

## 五、关键测量方法发现

1. **reasoning 模型需要足够的 `max_tokens`**：DeepSeek v4.1-flash 是 reasoning 模型，`finish_reason=length` + `reasoning_tokens=32` 说明 32 token 全被 reasoning 占满 → content 为空。`max_tokens=300` 解决（content='Paris'，correct=True）。
2. **真实上下文长度以 `prompt_tokens` 为准，前提是文件里有这个字段**。生成器用空白切分，并除以代码常量 `TOKEN_EXPANSION_RATIO = 1.26`。单针 1M 矩阵 JSON 没有 `prompt_tokens`（UNKNOWN）。带该字段的 results 文件在 seq_len=1000000 上的范围是 996353–996506（README claims block）。空白切分长度不是 API token 数。
3. **不要把另一个文件的 token 数抄到单针矩阵上**。results 文件里的 1M `prompt_tokens` 最大值是 996506（`data/multi-doc-qa-20261101-225024.json`）。

## 六、与文献对比（修正后视角）

| 来源 | 声称窗口 | 实测 | 结论 |
|------|---------|------|------|
| RULER (arXiv:2404.06654) | ≥32K | 约一半模型达标 | 长上下文能力 < 声称 |
| RULER v2 (Qwen3-235B) | 1M | 8K=87.3% → 1M=36.1% | 随长度递减 |
| **本测量 (stored scores, 2026-11-01)** | 1M flag | **saved single-needle cells are stored accuracy 1.0; prompt_tokens UNKNOWN** | **one checkpoint, not a ranking** |

> 注意：本测量用单针 NIAH，比 RULER 完整任务集（多针/多项选择/多文档）更简单。**RULER 完整任务集下可能看到衰减**——这是下一步测量方向。

## 七、复现

```bash
cd effective-context-lab
python3 scripts/run_benchmark.py --model opencode-go/deepseek-v4.1-flash --repeats 2 --max-tokens 300
```

原始数据:
- 基础矩阵: `data/final-benchmark-fixed-*.json`（30 cells）+ `data/1m-full-matrix-*.json`（25 cells）
- 深度扩展: `data/fine-position-benchmark-*.json`
- 任务扩展: `data/multi-needle-2-*.json`（20）+ `data/multi-choice-*.json`（25）+ `data/variable-tracking-*.json`（25）+ `data/aggregation-*.json`（20）+ `data/multi-doc-qa-*.json`（20）
- 补跑（备选模型 nvidia/deepseek-ai/deepseek-v4.1-flash，同一 DeepSeek v4.1 flash 不同 provider 路由）: `data/variable-tracking-1m-*.json` + `data/aggregation-*.json` + `data/multi-doc-qa-*.json`

---

## 八、任务复杂度扩展（RULER 完整任务集）

> 单针 NIAH 是最简单的任务。RULER 完整任务集还包括：多针检索、多项选择、变量追踪（Variable Tracking）、多文档问答、聚合。本节测量更复杂的任务，看模型在 1M 内是否仍保持能力。

### 8.1 多针检索（2 针, multi_needle）

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 65,536  | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**20/20 全部 1.00**（数据: `data/multi-needle-2-*.json`）。模型在 1M 内能同时检索 2 根针。

### 8.2 多项选择（multi_choice）

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 4,096   | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 65,536  | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**25/25 全部 1.00**（数据: `data/multi-choice-*.json`）。选项被嵌入干草堆（`Choices: Paris, Berlin, ...`），prompt 问 `Choose from the options`，模型需定位选项行再选。

### 8.3 变量追踪（variable_tracking, 带时间戳 t）

> 每个赋值标时间戳 `(t=1,2,3)`，问 `(final = t=3)` 的值。**模型需按 t 排序推理，不是读最后出现**（验证：所有种子下 t=3 出现顺序是中间，模型仍答 t=3 值）。

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 4,096   | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 65,536  | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Stored scores 22/22 + 3/3 = 25/25, two model ids**（`data/variable-tracking-20261101-200943.json` is `opencode-go/deepseek-v4.1-flash` and every `latency_ms` is 0; `data/variable-tracking-1m-20261101-215955.json` is `nvidia/deepseek-ai/deepseek-v4.1-flash`). Key overlap is 0. This is not one endpoint.

### 8.4 聚合（Aggregation, 需跨上下文求和）

> 8 个 item 各带值（`The value of item N is V.`），question 问 `sum of all item values`。**needle value 不在 context 中**，模型必须自己求和（跨上下文推理）。

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 65,536  | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**20/20 全部 1.00**（数据: `data/aggregation-*.json`）。模型在 1M 内能对 8 个分散 item 值求和。

### 8.5 多文档问答（Multi-doc QA, 跨文档定位）

> 8 个文档各 3 个事实，question 问**最后一个文档（document 8）的第一个事实**。模型必须定位目标文档并提取事实。

| seq_len | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---------|-----|------|-----|------|-----|
| 65,536  | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 262,144 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 524,288 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1,000,000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**20/20 全部 1.00**（数据: `data/multi-doc-qa-*.json`）。模型在 1M 内能跨 8 个文档定位并提取事实。

### 8.6 复杂度层级结论

| 任务 | 复杂度 | 1M 内表现 |
|------|-------|----------|
| 单针 NIAH | 检索（最简单） | 全部正确 |
| 多针检索 | 检索 | 全部正确 |
| 多项选择 | 检索+选择 | 全部正确 |
| 变量追踪 | 跨上下文追踪推理 | 全部正确 |
| 聚合（Aggregation） | 跨上下文求和 | 全部正确 |
| 多文档问答（Multi-doc QA） | 跨文档定位 | 全部正确 |

> **结论（stored scores only）**：上表各格的 stored score 为 1.0。这不是重算，也不是单一 model id。聚合与多文档问答、以及变量追踪的 3 个 1M 补点，model id 是 `nvidia/deepseek-ai/deepseek-v4.1-flash`；其余多数文件是 `opencode-go/deepseek-v4.1-flash`。单针矩阵没有 `prompt_tokens`。results 文件在 seq_len=1000000 上的 `prompt_tokens` 范围是 996353–996506。网格内没有低于 0.856 的格子，所以这些文件没有给出衰减边界。更长、更密或换针的任务没有在这里重跑。


---

## 九、文献综述（长上下文基准）

> 与长上下文评估基准的系统性综述，详见 `reports/LITERATURE-REVIEW.md`（10 篇论文，全部入库 Zotero collection「长上下文基准文献」key=ZMRSM3LI）。

### 9.1 基准发展脉络

| 代际 | 代表基准 | 特点 | 局限 |
|------|---------|------|------|
| 第一代（检索） | NIAH、RULER、BABILong、∞Bench | 合成任务，可复现 | 只能测检索，不测推理 |
| 第二代（真实任务） | LongBench v1/v2、LongBench Pro | 真实长文本，贴近应用 | 固定长度，无法分离基线 |
| 第三代（有效性批判） | 100-LongBench、Logic Haystacks | 质疑基准有效性 | 仍在发展中 |

### 9.2 与已有基准的核心对比

| 来源 | 结论 |
|------|------|
| RULER (arXiv:2404.06654) | 声称 ≥32K 仅约一半达标 |
| BABILong (arXiv:2406.10149) | LLM 有效利用仅 10-20% 上下文 |
| Logic Haystacks (arXiv:2502.17169) | 真实干扰物下 128 句即崩 |
| **本项目** | **stored score 1.0 on the saved grids; two model ids; not rescored** |

### 9.3 差异原因

1. **测量对象**：主文件里有两个 gateway model id，GLM 文件是另一个模型。这不是「当前最强」的排序。
2. **测量方法**：本项目用可控位置（0.0/0.25/0.5/0.75/1.0）× 长度（65K-1M）的探针矩阵，6 类任务。
3. **真实上下文长度**：只在 JSON 含 `prompt_tokens` 时才能引用。单针矩阵该字段为 UNKNOWN。results 文件的 1M 范围见 README claims block。
