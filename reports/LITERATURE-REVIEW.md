# 长上下文基准文献综述

> 与「长上下文有效利用率测量仪」相关的基准论文系统梳理（10 篇）。
> 全部已通过 paper_search/arXiv 验号并入库 Zotero collection「长上下文基准文献」（key: ZMRSM3LI）。

## 核心问题

长上下文模型声称的上下文窗口（context window）与实际有效窗口之间存在系统性差距。本综述梳理长上下文评估基准的发展脉络，说明本项目（Effective Context Lab）在其中的定位。

---

## 1. 第一代：单针检索基准（Needle In A Haystack, NIAH）

NIAH 是长上下文评估的经典范式：把「针」（目标信息）嵌入「干草堆」（无关文本），问模型能否定位。优点是简单可复现，缺点是**太简单**——只能测检索，不能测推理。

### 1.1 RULER（arXiv:2404.06654, COLM 2024, NVIDIA）

**作者**: Hsieh, Sun, Kriman, Acharya, Rekesh, Jia, Ginsburg
**GitHub**: NVIDIA/RULER
**核心结论**: 
- 声称 ≥32K 上下文的模型中，**仅约一半真正达到** 32K 阈值（0.856）。
- NIAH 近完美，但在更长上下文/更复杂任务大幅下降。
- RULER v2（Qwen3-235B）：8K=87.3% → 1M=36.1%，随长度递减。

**贡献**: 把 NIAH 扩展为 13 个任务（多针、多项选择、变量追踪、聚合、多文档问答等），是长上下文评估从「检索」到「推理」的分水岭。

**Zotero**: IEKFN9W9

### 1.2 BABILong（arXiv:2406.10149, NeurIPS 2024, 19 引用）

**作者**: Kuratov, Bulatov, Anokhin
**核心结论**: 
- **LLM 有效利用仅 10-20% 上下文**，性能随推理复杂度急剧下降。
- 20 个推理任务（事实链、归纳、演绎、计数、列表/集合处理），事实分散在超长自然文本中。

**贡献**: 证明 NIAH 低估了难度——推理型任务在长上下文中的衰减比检索型更严重。

**Zotero**: D2U7DJLW

### 1.3 ∞Bench/InfiniteBench（arXiv:2402.13718, ACL 2024, OpenBMB）

**作者**: Zhang, Yan, Zhou, Wang
**核心结论**: 100K+ token 长上下文基准，含数学、问答、摘要、代码等任务。

**Zotero**: DGE5LG7X

---

## 2. 第二代：真实任务基准（Real-Task Benchmarks）

NIAH 类合成任务被批评为「太不真实」。第二代基准改用真实长文本（书籍、论文、对话、代码库），更贴近实际应用，但引入新问题：固定序列长度、无法分离基线能力。

### 2.1 LongBench v1（arXiv:2308.14508, ACL 2024, 186 引用）

**作者**: Bai, Lv, Zhang, Lyu, Tang, Huang, Du, Liu, Zeng, Hou, Dong, Tang, Li
**核心结论**: 
- 首个**双语**（英/中）多任务长上下文基准。
- 21 个数据集、6 类任务，平均长度 6,711 词（英）/ 13,386 字（中）。
- 覆盖长文本应用场景（问答、摘要、翻译、代码、对话）。

**Zotero**: IRNV6NUB

### 2.2 LongBench v2（arXiv:2412.15204, ACL 2025, 29 引用）

**作者**: Bai, Tu, Zhang, Peng, Wang, Lv, Cao, Xu, Hou, Dong, Tang, Li
**核心结论**: 
- 503 道多项选择题，上下文 8K 到 2M 词。
- 6 类任务：单文档问答、多文档问答、长上下文学习、长对话历史理解、代码库理解、长结构化数据理解。
- **人类专家在 15 分钟限制下仅 53.7% 准确率**——基准本身很难。

**Zotero**: PXNKHTHV

### 2.3 LongBench Pro（arXiv:2601.02872, 2026）

**作者**: Chen, Wu, Jia
**核心结论**: 
- 1,500 个自然长上下文样本（英/中），11 个主任务、25 个子任务。
- 输入长度 8K 到 256K tokens。
- 多维分类法：上下文需求（全/部分依赖）、长度（6 级）、难度（4 级，按模型性能校准）。

**Zotero**: 9V2B4M9R

---

## 3. 第三代：基准有效性批判（Benchmark Validity）

随着基准越来越多，学界开始质疑：「这些基准真的在测长上下文能力吗？」

### 3.1 100-LongBench（arXiv:2505.19293, ACL Findings 2025）

**作者**: Yang, Jin, Zhong, Wang, Han, Zhou, Wang, Zhang, Peng
**核心结论**: 
- 长上下文基准有两个主要缺陷：
  1. **缺乏分离指标**：LongBench 类基准无法区分「长上下文能力」与「模型基线能力」，跨模型比较不清晰。
  2. **固定输入长度**：限制适用范围，无法揭示模型何时开始崩溃。
- 提出**长度可控**基准 + 新指标（解耦基线知识与真实长上下文能力）。

**Zotero**: UQ4C3PUB

### 3.2 Logic Haystacks（arXiv:2502.17169, EACL 2026 Short Papers）

**作者**: Sileo
**核心结论**: 
- 生成一阶逻辑表示的长文本（最高 2048 子句，约 25K GPT-4 tokens）。
- 用**真实干扰物**（难以与相关证据区分、证明不干扰）填充。
- **有效上下文窗口在真实干扰物下小得多，128 子句即开始崩溃**。

**贡献**: 证明「易识别的无关填充」会让 NIAH 高估能力；真实干扰物下有效窗口显著缩小。

**Zotero**: 7NL38Z6N

### 3.3 Challenging LLMs Beyond IR（Preprints 2024, DOI 10.20944/preprints202408.1527.v1）

**作者**: Fraga
**核心结论**: 
- 新基准「Find the Origin」：随上下文窗口增大，渐进测试简单智力任务。
- 14 个 LLM：**推理能力依赖输入大小**。
- GPT-4 Turbo 三次独立测试证实推理随输入大小衰减。

**Zotero**: UM6MSTUN

### 3.4 Hidden in the Haystack（arXiv:2505.18148, 2025）

**作者**: Bianchi, Koretsky, Sandu
**核心结论**: 
- 首次系统研究**金上下文大小**（gold context size）对长上下文问答的影响。
- 3 个基准（通用知识、生物医学推理、数学推理）、11 个 SOTA LLM、>150K 受控运行。
- **金上下文越短，模型性能越差**（小针更难找）。

**Zotero**: PTZS6ANB

---

## 4. 本项目（Effective Context Lab）的定位

### 与已有基准的差异

| 维度 | RULER | ∞Bench | BABILong | LongBench v2 | Logic Haystacks | **本项目** |
|------|-------|--------|----------|--------------|----------------|-----------|
| 测量对象 | 开源模型 | 开源模型 | 开源模型 | 开源模型 | 开源模型 | **Magpie 网关模型** |
| 上下文长度 | ≤1M | ≤100K+ | ≤100K+ | ≤2M 词 | ~25K tokens | **≤1M** |
| 任务类型 | 13 类 | 4 类 | 20 类 | 6 类 | 矛盾检测 | **6 类** |
| 模型权重 | 可访问 | 可访问 | 可访问 | 可访问 | 可访问 | **API 网关（不可访问）** |
| 主要结论 | 约一半达标 | — | 10-20% 利用 | 专家 53.7% | 128 句崩溃 | **stored score 1.0 on saved grids (see README claims block)** |

### 核心发现对比

| 来源 | 结论 |
|------|------|
| RULER | 几乎所有模型随长度大幅下降 |
| BABILong | LLM 有效利用仅 10-20% 上下文 |
| Logic Haystacks | 真实干扰物下 128 句即崩 |
| **本项目** | **stored score 1.0 on the saved grids; two gateway ids; not rescored; not a ranking** |

### 为什么本项目的发现不同

1. **测量对象不同**：文件里的 model id 有 `opencode-go/deepseek-v4.1-flash` 和 `nvidia/deepseek-ai/deepseek-v4.1-flash`，另有未纳入主表的 `volcengine/glm-5.3-flash`。这不是「当前最强」的排序。
2. **测量方法差异**：本项目用可控位置/密度的 NIAH 式探针（6 类任务），RULER 用固定任务集。本项目探针可精确控制针在干草堆中的位置（0.0/0.25/0.5/0.75/1.0）。
3. **真实上下文长度**：只在 JSON 含 `prompt_tokens` 时引用该字段。单针 1M 矩阵没有这个字段（UNKNOWN）。带该字段的 results 文件在 seq_len=1000000 上的范围见 README claims block（996353–996506）。空白切分长度不是 API token 数。

---

## 5. 参考文献（Zotero: 长上下文基准文献, key: ZMRSM3LI）

| 论文 | 作者 | 年份 | 来源 | Zotero key |
|------|------|------|------|-----------|
| RULER | Hsieh et al. | 2024 | COLM (arXiv:2404.06654) | IEKFN9W9 |
| BABILong | Kuratov et al. | 2024 | NeurIPS (arXiv:2406.10149) | D2U7DJLW |
| ∞Bench | Zhang et al. | 2024 | ACL (arXiv:2402.13718) | DGE5LG7X |
| LongBench v1 | Bai et al. | 2024 | ACL (arXiv:2308.14508) | IRNV6NUB |
| LongBench v2 | Bai et al. | 2025 | ACL (arXiv:2412.15204) | PXNKHTHV |
| 100-LongBench | Yang et al. | 2025 | ACL Findings (arXiv:2505.19293) | UQ4C3PUB |
| LongBench Pro | Chen et al. | 2026 | arXiv:2601.02872 | 9V2B4M9R |
| Logic Haystacks | Sileo | 2026 | EACL (arXiv:2502.17169) | 7NL38Z6N |
| Challenging LLMs Beyond IR | Fraga | 2024 | Preprints | UM6MSTUN |
| Hidden in the Haystack | Bianchi et al. | 2025 | arXiv:2505.18148 | PTZS6ANB |
