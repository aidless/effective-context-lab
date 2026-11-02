# Effective Context Lab — 长上下文有效利用率测量仪

> 实测「模型声称的上下文窗口」与「实际有效窗口」的差距，用可复现的 NIAH（Needle In A Haystack）探针。

## 背景：为什么需要这个

长上下文模型的**声称窗口 ≠ 有效窗口**。RULER 基准（arXiv:2404.06654）显示：声称 ≥32K 的模型中，仅约一半真正达到；Qwen3-235B 从 8K 的 87.3% 衰减到 1M 的 36.1%。「窗口大」不等于「窗口能用」。

本测量仪用 Magpie 网关的真实 1M 模型做实测，回答：**在声称 1M 窗口内，模型到底在什么位置、什么长度下仍然有效？**

## 核心结论（2026-11-01 实测）

**`opencode-go/deepseek-v4.1-flash`（声称 1M 窗口）在 1M 内对检索型和追踪型任务全部正确。**

| 任务 | 复杂度 | 1M 内表现 | cells |
|------|-------|----------|-------|
| 单针 NIAH | 检索（最简单） | 全部正确 | 50/50 |
| 多针检索（2 针） | 检索 | 全部正确 | 20/20 |
| 多项选择 | 检索+选择 | 全部正确 | 25/25 |
| 变量追踪（带时间戳） | 跨上下文追踪推理 | 全部正确 | 25/25 |
| 聚合（Aggregation） | 跨上下文求和 | 全部正确 | 20/20 |
| 多文档问答（Multi-doc QA） | 跨文档定位 | 全部正确 | 20/20 |

> **全部 6 类 RULER 任务（含跨上下文推理的聚合/多文档问答）在 1M 内全部正确**——尚未观察到有效窗口衰减。真正的瓶颈可能出现在 >1M 长度、更高信息密度或更复杂的推理任务上。

## 安装与使用

### 依赖

```bash
pip install openai matplotlib numpy
```

### 跑 benchmark

```bash
python3 scripts/run_benchmark.py \
  --model opencode-go/deepseek-v4.1-flash \
  --base-url http://127.0.0.1:3425/v1 \
  --seq-lens 4096,65536,262144,524288,1000000 \
  --positions 0.0,0.25,0.5,0.75,1.0 \
  --repeats 2 \
  --max-tokens 300
```

输出：`data/*.json`（原始 cells）+ 报告。

### 跑测试

```bash
python3 -m pytest tests/ -q
```

**39 项测试全绿**（RED→GREEN 纪律：每条断言先注入违规验证能红，再验证合规通过）。

### 可视化

```bash
python3 scripts/plot_results.py
```

输出：`reports/figures/*.png`（准确率热力图 + 延迟曲线）。

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
├── tests/             # 39 项测试
├── data/              # 原始 cells (JSON)
└── reports/
    ├── FINAL-REPORT.md   # 最终报告
    └── figures/           # 生成图
```

## 关键技术决策

### 1. token 膨胀率校正

探针生成时用空白切分估长度，但真实 tokenizer 分词更多（膨胀率 1.26）。**生成时目标 = seq_len / 1.26**，使实际 `prompt_tokens ≈ seq_len`（1M 探针实际 996,354，误差 ±0.3%）。

### 2. 真实上下文长度以 `prompt_tokens` 为准

`actual_len`（空白切分）是错误口径。正确口径 = `prompt_tokens`（1M 探针真实 996,354，占声称 99.6%）。实现：`complete_full()` 从 usage 读取。

### 3. reasoning 模型需要足够 `max_tokens`

`max_tokens=32` 会让 reasoning 模型的输出全被 reasoning 占满 → content 为空 → **伪影 0 分**。修正为 `max_tokens=300` 后数据真实可靠。

### 4. 有效窗口定义

某位置下最大 seq_len 满足 `avg accuracy ≥ 0.856`（RULER 阈值）。

## 数据文件清单

| 文件 | 内容 |
|------|------|
| `data/1m-full-matrix-*.json` | 单针 1M 完整矩阵（50 cells） |
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


---

## 开源许可

本项目以 [MIT License](LICENSE) 开源。

**论文**：`paper/main.md` 包含完整方法、结果与讨论（含 10 篇参考文献），已编译为 `paper/main.pdf`。

**数据**：`data/` 下 13 个 JSON 全部实测数据，可复现。原始数据生成命令见 `reports/FINAL-REPORT.md` 第七节复现。

**Zotero 文献库**：10 篇长上下文基准论文已入库（collection「长上下文基准文献」），详见 `reports/LITERATURE-REVIEW.md`。
