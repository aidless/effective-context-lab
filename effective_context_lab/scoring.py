"""评分器：测量模型回答与期望答案的一致性.

支持三种评分:
- exact_match: 精确匹配 (严格)
- f1_score:    F1 分数 (token 级, 容忍部分正确)
- multi_choice_accuracy: 多项选择准确率 (需在选项中选对)

RULER 惯例用 exact_match 或 multi_choice_accuracy; F1 用于容忍
模型在长上下文中"部分召回"的场景。
"""

from __future__ import annotations


def _normalize(text: str) -> str:
    """归一化: 小写、去标点、合并空白."""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def exact_match(prediction: str, expected: str) -> float:
    """精确匹配: 归一化后完全一致返回 1.0, 否则 0.0."""
    return 1.0 if _normalize(prediction) == _normalize(expected) else 0.0


def f1_score(prediction: str, expected: str) -> float:
    """token 级 F1 (精确率/召回率的调和平均).

    用于部分召回: 预测包含期望的一部分时给部分分。
    """
    pred_tokens = _normalize(prediction).split()
    exp_tokens = _normalize(expected).split()
    if not exp_tokens:
        return 0.0
    if not pred_tokens:
        return 0.0

    common = 0
    for t in exp_tokens:
        if t in pred_tokens:
            common += 1

    precision = common / len(pred_tokens) if pred_tokens else 0.0
    recall = common / len(exp_tokens) if exp_tokens else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def multi_choice_accuracy(prediction: str, expected: str, options: list[str] | None = None) -> float:
    """多项选择准确率.

    预测命中期望选项返回 1.0, 否则 0.0.
    如果 options 给出, 用选项内匹配 (预测需包含某个选项).
    """
    norm_pred = _normalize(prediction)
    norm_exp = _normalize(expected)

    if norm_exp in norm_pred:
        return 1.0
    # 尝试选项内匹配
    if options:
        for opt in options:
            if _normalize(opt) in norm_pred and _normalize(opt) == norm_exp:
                return 1.0
    return 0.0


def is_correct(prediction: str, expected: str, method: str = "exact_match") -> float:
    """统一评分入口."""
    if method == "exact_match":
        return exact_match(prediction, expected)
    if method == "f1":
        return f1_score(prediction, expected)
    if method == "multi_choice":
        return multi_choice_accuracy(prediction, expected)
    raise ValueError(f"Unknown scoring method: {method}")
