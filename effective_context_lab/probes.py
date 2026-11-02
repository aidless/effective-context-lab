"""探针生成器：NIAH 式可控长上下文探针.

实现 RULER (arXiv:2404.06654) 的 NIAH（Needle-in-a-Haystack）设计，
并扩展可控维度:
- 上下文长度 (seq_len)
- 针位置 (position_frac: 0=最前, 0.5=中间, 1=最后)
- 信息密度 (density: 关键事实 / 总 token 数)
- 任务类型 (单针 recall / 多针 / 多项选择)
- 针数量 (num_needles)

「声称窗口 ≠ 有效窗口」的核心测量: 同一位探针在越来越长的上下文中，
准确率随位置/密度衰减，跌到阈值处即有效窗口边界。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# RULER 阈值惯例: 以 Llama-2-7B@4K 的 85.6% 作为合格线
RULER_THRESHOLD = 0.856

# 任务类型
TaskType = Literal["single_needle", "multi_needle", "multi_choice", "variable_tracking", "aggregation", "multi_doc_qa"]


@dataclass
class NIAHConfig:
    """单个 NIAH 探针的配置."""

    seq_len: int = 4096
    """上下文总长度 (token 数)."""
    position_frac: float = 0.5
    """针在上下文中的相对位置 (0.0=最前, 0.5=中间, 1.0=最后)."""
    density: float = 1.0
    """信息密度: 每多少个 token 有 1 个关键事实 (越小越密)."""
    num_needles: int = 1
    """针数量 (1=单针, >1=多针)."""
    num_variables: int = 4
    """variable_tracking 任务的变量数."""
    num_assignments: int = 3
    """variable_tracking 任务每个变量的赋值次数."""
    num_docs: int = 8
    """multi_doc_qa 任务的文档数."""
    num_facts_per_doc: int = 3
    """multi_doc_qa 任务每文档的事实数."""
    aggregation_op: str = "sum"
    """aggregation 任务的聚合操作 (sum/count/avg)."""
    task: TaskType = "single_needle"
    """任务类型."""
    needle_subject: str = "the capital of France"
    needle_value: str = "Paris"
    """针的内容 (subject->value)."""
    haystack_filler: str = "The grass is green. The sky is blue. The sun is bright."
    """干草堆填充文本 (低信息)."""
    seed: int = 42
    """随机种子，保证可复现."""
    max_output_tokens: int = 32
    """每个探针请求的最大输出 token."""


@dataclass
class Needle:
    """一根针 (关键事实)."""

    subject: str
    value: str
    position: int = 0
    """针在上下文中的绝对 token 位置."""


def _tokenize(text: str) -> list[str]:
    """粗略 token 化: 按空白切分 (探针只需近似长度, 精确分词留给客户端)."""
    return text.split()


# 实测 token 膨胀率 (DeepSeek tokenizer 对英文填充文本, 2026-11-01 实测):
# 目标 4096 -> 实际 5187 (1.27x); 目标 8192 -> 实际 10335 (1.26x); 目标 131072 -> 实际 164591 (1.26x)
TOKEN_EXPANSION_RATIO = 1.26


def _adjust_seq_for_tokenizer(seq_len: int) -> int:
    """校正目标 seq_len: 由于 tokenizer 分词膨胀, 生成时用调整后的目标.

    实际返回的 prompt_tokens ≈ seq_len (用膨胀率校正).
    """
    return max(1, int(seq_len / TOKEN_EXPANSION_RATIO))


def needle_position(seq_len: int, position_frac: float) -> int:
    """计算针的绝对 token 位置.

    Args:
        seq_len: 上下文总长度.
        position_frac: 相对位置 (0.0~1.0).

    Returns:
        绝对位置 (int), 保证在 [1, seq_len-2] 内 (避开首尾边界).
    """
    if not (0.0 <= position_frac <= 1.0):
        raise ValueError(f"position_frac must be in [0,1], got {position_frac}")
    raw = int(seq_len * position_frac)
    # 避开首尾: 至少留 1 个 token 在针两侧
    return max(1, min(seq_len - 2, raw))


def generate_needle(
    config: NIAHConfig,
    needle_index: int = 0,
) -> str:
    """生成单根针的句子文本."""
    return f"The {config.needle_subject} is {config.needle_value}."


def generate_needle_in_haystack(config: NIAHConfig) -> tuple[str, list[Needle], int]:
    """生成一个 NIAH 探针.

    Returns:
        (context_text, needles, actual_seq_len)
        - context_text: 完整的上下文文本 (haystack + needles)
        - needles: 针列表 (含绝对位置)
        - actual_seq_len: 实际生成的 token 数
    """
    import random

    rng = random.Random(config.seed)

    # 针文本
    needles: list[Needle] = []
    needle_texts: list[str] = []

    if config.task == "multi_choice":
        # 多项选择: 一个 subject 对应一个 value, 但生成 4 个选项
        subject = config.needle_subject
        value = config.needle_value
        distractors = ["Berlin", "Madrid", "Rome", "Lisbon"]
        # 排除正确值
        distractors = [d for d in distractors if d != value][:3]
        options = [value] + distractors
        rng.shuffle(options)
        n = Needle(subject=subject, value=value)
        needles.append(n)
        needle_texts.append(f"The {subject} is {value}.")
        # 选项嵌入提示
        opts = ", ".join(options)
        needle_texts.append(f"Choices: {opts}")
    elif config.task == "variable_tracking":
        # 变量追踪 (RULER Variable Tracking): 多个变量多次赋值, 问某变量最终值
        # 升级版: 每个赋值标时间戳 t, 问 t=num_assignments 的值 (需排序推理)
        num_variables = max(2, getattr(config, "num_variables", 4))
        num_assignments = max(2, getattr(config, "num_assignments", 3))
        # 生成变量赋值: 每个变量赋值 num_assignments 次, 值递增
        var_values: dict[int, list[int]] = {}
        for v in range(1, num_variables + 1):
            # 用种子控制起始值, 保证可复现
            base = rng.randint(1, 50) + v * 100
            vals = [base + i * 10 for i in range(num_assignments)]
            var_values[v] = vals
        # 把赋值分散到不同位置 (通过打乱顺序), 但每条标 t
        assignments: list[tuple[int, int, int]] = []  # (var, t, value)
        for v in range(1, num_variables + 1):
            for t, val in enumerate(var_values[v], start=1):
                assignments.append((v, t, val))
        rng.shuffle(assignments)
        # 生成赋值文本, 每条独立句子 + 时间戳
        var_texts = []
        for v, t, val in assignments:
            var_texts.append(f"Variable {v} = {val} (t={t}).")
        # 针: 问最后一个变量 (最难: 需要跨上下文追踪)
        target_var = num_variables
        target_val = var_values[target_var][-1]  # 最终值 = t=num_assignments 的值
        n = Needle(subject=f"variable {target_var}", value=str(target_val))
        needles.append(n)
        needle_texts.extend(var_texts)
    elif config.task == "aggregation":
        # 聚合任务 (RULER Aggregation): 多个数值需要求和/计数/平均
        # 生成多个分散的数值事实, 问它们的聚合结果
        n_facts = max(3, min(10, config.num_variables * 2))
        # 用种子生成可复现的数值
        values = [rng.randint(1, 99) for _ in range(n_facts)]
        # 事实文本分散在干草堆中
        fact_texts = []
        for i, val in enumerate(values):
            fact_texts.append(f"The value of item {i+1} is {val}.")
        # 针: 问聚合结果
        if config.aggregation_op == "sum":
            target = sum(values)
            needle_desc = f"the sum of all item values"
        elif config.aggregation_op == "avg":
            target = round(sum(values) / len(values), 2)
            needle_desc = f"the average of all item values"
        else:  # count
            target = len(values)
            needle_desc = f"the count of all items"
        n = Needle(subject=needle_desc, value=str(target))
        needles.append(n)
        needle_texts.extend(fact_texts)
    elif config.task == "multi_doc_qa":
        # 多文档问答 (RULER Multi-doc QA): 多文档, 每文档有唯一事实
        # 问某文档的关键事实 (需要跨文档定位)
        n_docs = max(2, config.num_docs)
        n_facts = max(1, config.num_facts_per_doc)
        doc_texts = []
        doc_facts: dict[int, list[tuple[str, str]]] = {}
        for d in range(1, n_docs + 1):
            facts = []
            for f in range(1, n_facts + 1):
                # 每文档唯一主题与值
                subject = f"key fact {f} of document {d}"
                val = f"value_{d}_{f}"
                facts.append((subject, val))
                doc_texts.append(f"Document {d}: The {subject} is {val}.")
            doc_facts[d] = facts
        # 针: 问最后一个文档的第一个事实 (需要跨文档定位)
        target_doc = n_docs
        target_subject, target_val = doc_facts[target_doc][0]
        n = Needle(subject=target_subject, value=target_val)
        needles.append(n)
        needle_texts.extend(doc_texts)
    else:
        # 单针或多针
        num = max(1, config.num_needles)
        for i in range(num):
            subject = config.needle_subject
            if num > 1:
                subject = f"{config.needle_subject} {i+1}"
            # 注意: 多针时 subject 带序号(区分不同针), 但 value 不带序号
            # 因为模型回答 'What is the capital of France 1?' 时会答 'Paris' 而不是 'Paris 1'
            # 若 value 也带序号, exact_match('Paris', 'Paris 1') = False (bug)
            value = config.needle_value
            n = Needle(subject=subject, value=value)
            needles.append(n)
            needle_texts.append(f"The {subject} is {value}.")

    # 干草堆填充: 需要达到 config.seq_len
    # 用 tokenizer 膨胀率校正: 生成时目标是 seq_len / 1.26, 实际 prompt ≈ seq_len
    target_len = _adjust_seq_for_tokenizer(config.seq_len)
    base_filler = config.haystack_filler
    filler_variants = [
        base_filler,
        "The ocean is deep. The mountains are tall. The rivers flow.",
        "The forest is dense. The desert is dry. The snow is cold.",
        "The city is busy. The village is quiet. The farm is green.",
    ]
    filler_tokens = _tokenize(base_filler)
    needle_tokens = sum(len(_tokenize(t)) for t in needle_texts)
    remaining = max(0, target_len - needle_tokens)

    # 构建干草堆基础 (用种子选择变体，保证不同种子生成不同内容)
    haystack_parts: list[str] = []
    current_tokens = 0
    variant_idx = 0
    while current_tokens < remaining:
        # 每段用变体，种子决定起始变体
        variant = filler_variants[(config.seed + variant_idx) % len(filler_variants)]
        haystack_parts.append(variant)
        current_tokens += len(_tokenize(variant))
        variant_idx += 1

    haystack_text = " ".join(haystack_parts)
    haystack_tokens = _tokenize(haystack_text)

    # 将针插入到指定位置 (用校正后的目标长度)
    target_pos = needle_position(target_len, config.position_frac)

    # 拼接: haystack[0:target_pos] + needle + haystack[target_pos:]
    # 用 token 定位
    h_tokens = haystack_tokens
    insert_at = min(target_pos, len(h_tokens))

    context_parts = h_tokens[:insert_at]
    for nt in needle_texts:
        context_parts.extend(_tokenize(nt))
    context_parts.extend(h_tokens[insert_at:])

    context_text = " ".join(context_parts)
    actual_len = len(_tokenize(context_text))

    # 更新针的绝对位置 (近似)
    for i, n in enumerate(needles):
        n.position = min(insert_at + i * len(_tokenize(needle_texts[i])), actual_len - 1)

    return context_text, needles, actual_len


def generate_question(config: NIAHConfig, needles: list[Needle]) -> str:
    """根据任务类型生成问题."""
    if config.task == "multi_choice":
        return f"What is {config.needle_subject}? Choose from the options."
    if config.task == "multi_needle":
        # 多针: 问第一根
        return f"What is {needles[0].subject}?"
    if config.task == "variable_tracking":
        # 变量追踪: 问目标变量最终值 (t=num_assignments)
        return f"What is the final value of {needles[0].subject}? (final = t={config.num_assignments}) Give just the number."
    if config.task == "aggregation":
        # 聚合: 问所有数值的聚合结果
        op_desc = {"sum": "sum", "avg": "average", "count": "count"}.get(config.aggregation_op, "sum")
        return f"What is {op_desc} of all item values? Give just the number."
    if config.task == "multi_doc_qa":
        # 多文档问答: 问最后一个文档的事实
        return f"What is {needles[0].subject}?"
    return f"What is {config.needle_subject}?"


def expected_answer(config: NIAHConfig, needles: list[Needle]) -> str:
    """期望答案."""
    if config.task == "multi_choice":
        return config.needle_value
    if config.task == "multi_needle":
        return needles[0].value
    if config.task == "variable_tracking":
        return needles[0].value
    if config.task == "aggregation":
        return needles[0].value
    if config.task == "multi_doc_qa":
        return needles[0].value
    return config.needle_value
