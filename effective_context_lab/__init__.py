"""effective-context-lab: 长上下文有效利用率测量仪.

测量「声称窗口 vs 有效窗口」之间的鸿沟（RULER 式 NIAH 探针 + 可控任务复杂度）。

四层结构:
- probes:    探针生成器（NIAH 单针/多针、位置、密度、任务类型可控）
- scoring:   评分器（精确匹配 / F1 / 多项选择正确率）
- clients:   模型客户端（OpenAI 兼容，Magpie 1M 网关 / mock）
- runner:    benchmark 运行器（多长度×多位置×多密度扫描）

核心口径: 有效窗口 = 在给定位置/密度下保持阈值准确率的最大上下文长度。
"""

from .probes import (
    NIAHConfig,
    Needle,
    generate_needle,
    generate_needle_in_haystack,
    needle_position,
)
from .scoring import (
    exact_match,
    f1_score,
    multi_choice_accuracy,
    is_correct,
)
from .clients import (
    ModelClient,
    OpenAICompatClient,
    MockClient,
    get_client,
)
from .runner import (
    BenchmarkConfig,
    BenchmarkResult,
    ProbeCase,
    run_probe,
    run_benchmark,
)

__version__ = "0.1.0"

__all__ = [
    "NIAHConfig",
    "Needle",
    "generate_needle",
    "generate_needle_in_haystack",
    "needle_position",
    "exact_match",
    "f1_score",
    "multi_choice_accuracy",
    "is_correct",
    "ModelClient",
    "OpenAICompatClient",
    "MockClient",
    "get_client",
    "BenchmarkConfig",
    "BenchmarkResult",
    "ProbeCase",
    "run_probe",
    "run_benchmark",
]
