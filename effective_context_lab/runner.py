"""Benchmark 运行器：多长度 × 多位置 × 多密度扫描.

产出 BenchmarkResult，含:
- 每个 (seq_len, position, density) 单元格的准确率
- 有效窗口: 保持阈值准确率的最大上下文长度
- 声称 vs 有效窗口的鸿沟

核心口径 (对齐九号章节):
  有效窗口 = 在给定位置/密度下, 准确率 >= RULER_THRESHOLD 的最大 seq_len。
  声称窗口 = 模型的 context_length (来自客户端)。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from .clients import ModelClient
from .probes import NIAHConfig, generate_needle_in_haystack, generate_question, expected_answer
from .scoring import is_correct


@dataclass
class ProbeCase:
    """单个探针用例 (已生成)."""

    config: NIAHConfig
    context: str
    question: str
    expected: str
    actual_len: int
    needle_positions: list[int] = field(default_factory=list)


@dataclass
class BenchmarkConfig:
    """Benchmark 扫描配置."""

    seq_lens: list[int] = field(
        default_factory=lambda: [4096, 8192, 16384, 32768, 65536, 131072]
    )
    position_fracs: list[float] = field(default_factory=lambda: [0.0, 0.5, 1.0])
    densities: list[float] = field(default_factory=lambda: [1.0])
    task: str = "single_needle"
    repeats: int = 1
    """每个单元格重复次数 (取均值)."""
    threshold: float = 0.856
    """合格阈值 (RULER 惯例)."""
    max_tokens: int = 300
    seed: int = 42
    system_prompt: str = "You are a helpful assistant. Answer the question with one word."


@dataclass
class CellResult:
    """单个 (seq_len, position, density) 单元格的结果."""

    seq_len: int
    position_frac: float
    density: float
    accuracy: float
    n_cases: int
    latencies_ms: list[float] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    """Benchmark 结果."""

    model: str
    claimed_context: int
    config: BenchmarkConfig
    cells: list[CellResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    def cell(self, seq_len: int, position_frac: float, density: float) -> CellResult | None:
        for c in self.cells:
            if c.seq_len == seq_len and c.position_frac == position_frac and c.density == density:
                return c
        return None

    def effective_window(
        self,
        position_frac: float = 0.0,
        density: float = 1.0,
    ) -> int:
        """有效窗口: 该位置/密度下保持阈值准确率的最大 seq_len."""
        best = 0
        for c in self.cells:
            if c.position_frac == position_frac and c.density == density and c.accuracy >= self.config.threshold:
                best = max(best, c.seq_len)
        return best

    def claimed_vs_effective(
        self,
        position_frac: float = 0.0,
        density: float = 1.0,
    ) -> dict[str, float | int]:
        """声称 vs 有效窗口的鸿沟."""
        eff = self.effective_window(position_frac, density)
        return {
            "claimed": self.claimed_context,
            "effective": eff,
            "ratio": (eff / self.claimed_context) if self.claimed_context else 0.0,
            "gap": self.claimed_context - eff,
        }

    def to_dict(self) -> dict[str, Any]:
        """转为 dict."""
        return {
            "model": self.model,
            "claimed_context": self.claimed_context,
            "config": {
                "seq_lens": self.config.seq_lens,
                "position_fracs": self.config.position_fracs,
                "densities": self.config.densities,
                "task": self.config.task,
                "repeats": self.config.repeats,
                "threshold": self.config.threshold,
                "seed": self.config.seed,
            },
            "cells": [
                {
                    "seq_len": c.seq_len,
                    "position_frac": c.position_frac,
                    "density": c.density,
                    "accuracy": c.accuracy,
                    "n_cases": c.n_cases,
                    "avg_latency_ms": (sum(c.latencies_ms) / len(c.latencies_ms)) if c.latencies_ms else 0.0,
                }
                for c in self.cells
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _build_case(config: NIAHConfig) -> ProbeCase:
    """构建一个探针用例."""
    context, needles, actual_len = generate_needle_in_haystack(config)
    question = generate_question(config, needles)
    expected = expected_answer(config, needles)
    return ProbeCase(
        config=config,
        context=context,
        question=question,
        expected=expected,
        actual_len=actual_len,
        needle_positions=[n.position for n in needles],
    )


def run_probe(
    client: ModelClient,
    config: NIAHConfig,
    *,
    system_prompt: str = "You are a helpful assistant. Answer with one word.",
) -> dict[str, Any]:
    """运行单个探针，返回评分结果."""
    case = _build_case(config)
    prompt = (
        f"Context:\n{case.context}\n\n"
        f"Question: {case.question}\n"
        f"Answer (one word):"
    )
    if getattr(client, "oracle", False):
        primer = getattr(client, "prime_expected", None)
        if callable(primer):
            primer(case.expected)
    t0 = time.time()
    resp = client.complete_full(
        prompt,
        system=system_prompt,
        max_tokens=config.max_output_tokens,
    )
    latency_ms = (time.time() - t0) * 1000.0
    prediction = resp["content"]
    # 0 means the client did not report usage. Do not substitute the
    # whitespace length: that number is not an API prompt_tokens count.
    reported_tokens = resp.get("prompt_tokens") or 0
    prompt_tokens = int(reported_tokens)
    score = is_correct(prediction, case.expected, method="exact_match")
    return {
        "score": score,
        "prediction": prediction,
        "expected": case.expected,
        "latency_ms": latency_ms,
        "actual_len": case.actual_len,
        "prompt_tokens": prompt_tokens,
        "finish_reason": resp.get("finish_reason"),
        "needle_positions": case.needle_positions,
    }


def run_benchmark(
    client: ModelClient,
    config: BenchmarkConfig,
    *,
    progress: bool = True,
) -> BenchmarkResult:
    """运行完整 benchmark 扫描."""
    result = BenchmarkResult(
        model=client.model,
        claimed_context=client.context_length if hasattr(client, "context_length") else 0,
        config=config,
    )

    total = (
        len(config.seq_lens)
        * len(config.position_fracs)
        * len(config.densities)
        * config.repeats
    )
    done = 0

    for seq_len in config.seq_lens:
        for position_frac in config.position_fracs:
            for density in config.densities:
                scores: list[float] = []
                latencies: list[float] = []
                for _ in range(config.repeats):
                    niah_cfg = NIAHConfig(
                        seq_len=seq_len,
                        position_frac=position_frac,
                        density=density,
                        task=config.task,  # type: ignore[arg-type]
                        seed=config.seed + done,
                        max_output_tokens=config.max_tokens,
                    )
                    r = run_probe(client, niah_cfg, system_prompt=config.system_prompt)
                    scores.append(r["score"])
                    latencies.append(r["latency_ms"])
                    done += 1
                    if progress:
                        print(f"  [{done}/{total}] seq={seq_len} pos={position_frac} dens={density} score={r['score']:.2f}", flush=True)

                accuracy = sum(scores) / len(scores) if scores else 0.0
                result.cells.append(
                    CellResult(
                        seq_len=seq_len,
                        position_frac=position_frac,
                        density=density,
                        accuracy=accuracy,
                        n_cases=len(scores),
                        latencies_ms=latencies,
                    )
                )

    result.finished_at = time.time()
    return result
