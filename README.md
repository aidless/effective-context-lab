# Effective Context Lab — 长上下文有效利用率测量仪

> 实测「模型声称的上下文窗口」与「实际有效窗口」的差距，用可复现的 NIAH（Needle In A Haystack）探针。

## 背景：为什么需要这个

长上下文模型的**声称窗口 ≠ 有效窗口**。RULER v1（arXiv:2404.06654）显示：声称 ≥32K 的模型中，仅约一半真正达到。RULER v2（2026 复现表，Qwen3-235B）进一步给出量化衰减：8K 时 87.3% → 1M 时 36.1%。「窗口大」不等于「窗口能用」。

> 引用边界：arXiv:2404.06654 是 RULER **v1**（2024-04，评测 17 个模型），其中不含 Qwen3-235B；上句后半段的 87.3%→36.1% 来自 RULER **v2** 的复现表（见 `reports/FINAL-REPORT.md` 与 `reports/LITERATURE-REVIEW.md`）。v2 的 arXiv ID 本仓未收录，故此处不附编号。

本测量仪用 Magpie 网关的真实 1M 模型做实测，回答：**在声称 1M 窗口内，模型到底在什么位置、什么长度下仍然有效？**

## 核心结论（2026-11-01 实测）

**`opencode-go/deepseek-v4.1-flash`（声称 1M 窗口）在 1M 内对检索型和追踪型任务全部正确。**

| 任务 | 复杂度 | 1M 内表现 | 正确数 | 数据载体 |
|------|-------|----------|--------|----------|
| 单针 NIAH | 检索（最简单） | 全部正确 | 50/50 cases（25 cells × repeats=2） | `data/1m-full-matrix-*.json` |
| 多针检索（2 针） | 检索 | 全部正确 | 20/20 | `data/multi-needle-2-*.json` |
| 多项选择 | 检索+选择 | 全部正确 | 25/25 | `data/multi-choice-*.json` |
| 变量追踪（带时间戳） | 跨上下文追踪推理 | 全部正确 | 25/25 | `data/variable-tracking-*.json` + `data/variable-tracking-1m-*.json` |
| 聚合（Aggregation） | 跨上下文求和 | 全部正确 | 20/20 | `data/aggregation-*.json` |
| 多文档问答（Multi-doc QA） | 跨文档定位 | 全部正确 | 20/20 | `data/multi-doc-qa-*.json` |

> 「cells」= (seq_len × position) 的网格点；「cases」= 网格点 × repeats。
> 单针 1M 完整矩阵是 **25 cells / 50 cases**；其余任务是每点 1 次，即 rows 数 = cases 数。

> **全部 6 类 RULER 任务（含跨上下文推理的聚合/多文档问答）在 1M 内全部正确**——尚未观察到有效窗口衰减。真正的瓶颈可能出现在 >1M 长度、更高信息密度或更复杂的推理任务上。

## 安装与使用

### 依赖

```bash
pip install matplotlib numpy pytest
```

> `effective_context_lab` 包本身只用 Python 标准库（`urllib.request` 走 OpenAI 兼容协议）；
> `matplotlib` / `numpy` 只有 `scripts/plot_results.py` 需要，`pytest` 只有跑测试需要。
> 另有可选的本地模型后端用 `numpy`（`clients.py` 的 `MockClient`）。

### 跑 benchmark

```bash
python3 scripts/run_benchmark.py \
  --model opencode-go/deepseek-v4.1-flash \
  --base-url http://127.0.0.1:3425/v1 \
  --seq-lens 4096 65536 262144 524288 1000000 \
  --positions 0.0 0.25 0.5 0.75 1.0 \
  --repeats 2 \
  --seed 7 \
  --max-tokens 300
```

> `--seq-lens` / `--positions` 是 `nargs="+"`，**必须空格分隔**；写成逗号分隔会直接
> `invalid int value: '4096,65536,...'` 退出 2。
> `--base-url` 默认指向本机 Magpie 网关（`127.0.0.1:3425`）；换一个 OpenAI 兼容端点即可。
> 客户端不带鉴权头（`api_key` 默认为空）；若端点需要 key，目前只能改 `clients.py` 的默认值
> —— 本仓**没有** `--api-key` 开关，也没有读环境变量的路径。

输出：`data/*.json`（原始 cells）+ 报告。

### 跑测试

```bash
python3 -m pytest tests/ -q
```

**44 项测试全绿**（RED→GREEN 纪律：每条断言先注入违规验证能红，再验证合规通过）。
分文件：test_clients 5 + test_probes 20 + test_runner 6 + test_scoring 13 = 44。

### 可视化

```bash
python3 scripts/plot_results.py
```

输出：`reports/figures/*.png`（准确率热力图 + 延迟曲线）。当前脚本生成 5 张：
`heatmap-1m` / `heatmap-multineedle` / `heatmap-multichoice` / `heatmap-variable-tracking` / `latency`；
`aggregation` 与 `multi-doc-qa` 的热力图脚本里暂无对应分支，仓内也无这两张图。

## 项目结构

```
effective-context-lab/
├── effective_context_lab/
│   ├── probes.py      # NIAH 探针生成器 (单针/多针/多项选择/变量追踪/聚合/多文档)
│   ├── scoring.py     # 评分 (exact_match/f1/multi_choice)
│   ├── clients.py     # 模型客户端 (OpenAICompat/Mock + complete_full)
│   └── runner.py      # benchmark 运行器 (run_probe/run_benchmark)
├── scripts/
│   ├── run_benchmark.py   # CLI 入口
│   └── plot_results.py    # 可视化
├── tests/             # 44 项测试
├── data/              # 原始 cells (JSON)
└── reports/
    ├── FINAL-REPORT.md   # 最终报告
    └── figures/           # 生成图
```

## 关键技术决策

### 1. token 膨胀率校正

探针生成时用空白切分估长度，但真实 tokenizer 分词更多（膨胀率 1.26）。**生成时目标 = seq_len / 1.26**，使实际 `prompt_tokens ≈ seq_len`（单针 1M 探针实际 996,354，误差 0.365%；各任务 max prompt_tokens 略有差异：multi-needle-2 996,353 / multi-choice 996,354 / aggregation 996,364 / variable-tracking 996,419 / multi-doc-qa 996,506）。

### 2. 真实上下文长度以 `prompt_tokens` 为准

`actual_len`（空白切分）是错误口径。正确口径 = `prompt_tokens`（单针 1M 探针真实 996,354，占声称 99.635%）。实现：`complete_full()` 从 usage 读取。

### 3. reasoning 模型需要足够 `max_tokens`

`max_tokens=32` 会让 reasoning 模型的输出全被 reasoning 占满 → content 为空 → **伪影 0 分**。修正为 `max_tokens=300` 后数据真实可靠。

### 4. 有效窗口定义

某位置下最大 seq_len 满足 `avg accuracy ≥ 0.856`（RULER 阈值）。

## 数据文件清单

| 文件 | 内容 |
|------|------|
| `data/1m-full-matrix-*.json` | 单针 1M 完整矩阵（25 cells / 50 cases） |
| `data/multi-needle-2-*.json` | 多针检索（20 cells） |
| `data/multi-choice-*.json` | 多项选择（25 cells） |
| `data/variable-tracking-*.json` | 变量追踪（25 cells） |
| `data/aggregation-*.json` | 聚合（20 cells） |
| `data/multi-doc-qa-*.json` | 多文档问答（20 cells） |

## 已知限制

- **测量对象单一**：仅 `opencode-go/deepseek-v4.1-flash`（Magpie 网关）。GLM-5.3 数据不可靠（服务端限流），未纳入主对比。
- **配额限制**：OpenCode Go 每日配额用尽会返回 429（错误消息 `Go usage limit exceeded`），需等待 22:32 UTC-8 恢复。
- **任务覆盖**：6 类 RULER 任务已全部测量（单针/多针/多项选择/变量追踪/聚合/多文档问答），1M 内全部正确。
- **文献对比**：本测量与 RULER/∞Bench/BABILong/LongBench 系列同类，但用 Magpie 网关测 DeepSeek v4.1 flash（非开源模型权重），1M 内 6 类任务全对，RULER 原论文「几乎所有模型随长度大幅下降」的结论在本测量中未复现。

## 复现

所有数字来自 `data/*.json` 原始 cells，可重算。报告：`reports/FINAL-REPORT.md`。

逐文件对应的生成命令（参数取自各文件 `config` / `results` 块，与仓内产物一致）：

```bash
# 单针 1M 完整矩阵 → data/1m-full-matrix-*.json（25 cells × repeats=2 = 50 cases）
python3 scripts/run_benchmark.py --task single_needle \
  --seq-lens 4096 65536 262144 524288 1000000 \
  --positions 0.0 0.25 0.5 0.75 1.0 --repeats 2 --seed 7 --max-tokens 300

# 多针 / 多项选择 / 变量追踪 / 聚合 / 多文档（每点 1 次）
python3 scripts/run_benchmark.py --task multi_needle   --seq-lens 65536 262144 524288 1000000 --positions 0.0 0.25 0.5 0.75 1.0 --repeats 1 --max-tokens 300
python3 scripts/run_benchmark.py --task multi_choice   --seq-lens 4096 65536 262144 524288 1000000 --positions 0.0 0.25 0.5 0.75 1.0 --repeats 1 --max-tokens 300
python3 scripts/run_benchmark.py --task variable_tracking --seq-lens 4096 65536 262144 524288 1000000 --positions 0.0 0.25 0.5 0.75 1.0 --repeats 1 --max-tokens 300
python3 scripts/run_benchmark.py --task aggregation     --seq-lens 65536 262144 524288 1000000 --positions 0.0 0.25 0.5 0.75 1.0 --repeats 1 --max-tokens 300
python3 scripts/run_benchmark.py --task multi_doc_qa    --seq-lens 65536 262144 524288 1000000 --positions 0.0 0.25 0.5 0.75 1.0 --repeats 1 --max-tokens 300
```

> 各次运行的**输出文件名带时间戳**，不会覆盖既有产物；重跑后请与 `data/` 中同名旧文件比对。
> `data/` 下另有 4 个**失败或被取代**的 run（`final-benchmark-20261101-175003.json`、
> `fine-position-benchmark-*.json`、`glm53-benchmark-*.json`，
> `opencode-go-*-benchmark-*.json`），`min accuracy` 分别为 0.0 / 0.0 / 0.0 / 0.5，
> 对应 README「已知限制」里讲的 `max_tokens=32` 伪影、GLM 限流放弃等情形——
> 它们不是最终结果，引用时不要混用。


---

## 开源许可

本项目以 [MIT License](LICENSE) 开源。

**论文**：`paper/main.md` 包含完整方法、结果与讨论（含 10 篇参考文献），已编译为 `paper/main.pdf`。

**数据**：`data/` 下 13 个 JSON 全部为实测数据（含 4 个失败/被取代的 run，见上文「复现」一节的区分）。逐文件的生成命令见上文「复现」一节。

**Zotero 文献库**：10 篇长上下文基准论文已入库（collection「长上下文基准文献」），详见 `reports/LITERATURE-REVIEW.md`。
