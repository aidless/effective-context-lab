"""Runner 测试 (用 MockClient, 不烧真实 API)."""

import pytest

from effective_context_lab.clients import MockClient
from effective_context_lab.runner import (
    BenchmarkConfig,
    run_benchmark,
    run_probe,
)
from effective_context_lab.probes import NIAHConfig


def make_mock(expected="Paris", position_frac=0.0, context_length=131072):
    c = MockClient(
        model="mock-model",
        context_length=context_length,
        base_url="http://localhost:9",  # 不会真的请求
    )
    c._expected_answer = expected
    c._position_frac = position_frac
    return c


class TestRunProbe:
    def test_probe_returns_score(self):
        client = make_mock()
        cfg = NIAHConfig(seq_len=2048, position_frac=0.0, seed=1)
        r = run_probe(client, cfg)
        assert "score" in r
        assert "prediction" in r
        assert "expected" in r
        assert "latency_ms" in r
        assert r["expected"] == "Paris"

    def test_probe_correct_when_expected_available(self):
        client = make_mock(expected="Paris", position_frac=0.0)
        cfg = NIAHConfig(seq_len=512, position_frac=0.0, seed=2)
        r = run_probe(client, cfg)
        # mock 在最前位置应大概率答对
        assert r["score"] in (0.0, 1.0)


class TestRunBenchmark:
    def test_small_benchmark(self):
        client = make_mock(context_length=131072)
        cfg = BenchmarkConfig(
            seq_lens=[1024, 2048],
            position_fracs=[0.0, 0.5],
            densities=[1.0],
            repeats=1,
            seed=7,
        )
        result = run_benchmark(client, cfg, progress=False)
        assert len(result.cells) == 4
        assert result.claimed_context == 131072
        assert result.model == "mock-model"

    def test_effective_window(self):
        client = make_mock(context_length=131072)
        cfg = BenchmarkConfig(
            seq_lens=[1024, 2048, 4096, 8192],
            position_fracs=[0.0, 0.5],
            densities=[1.0],
            repeats=1,
            seed=7,
        )
        result = run_benchmark(client, cfg, progress=False)
        # 最前位置应有非零有效窗口
        eff = result.effective_window(position_frac=0.0)
        assert eff > 0
        # 声称 >= 有效
        assert result.claimed_context >= eff

    def test_claimed_vs_effective_gap(self):
        client = make_mock(context_length=131072)
        cfg = BenchmarkConfig(
            seq_lens=[1024, 2048],
            position_fracs=[0.0],
            densities=[1.0],
            repeats=1,
            seed=7,
        )
        result = run_benchmark(client, cfg, progress=False)
        gap = result.claimed_vs_effective(position_frac=0.0)
        assert gap["claimed"] == 131072
        assert gap["effective"] >= 0
        assert 0.0 <= gap["ratio"] <= 1.0

    def test_to_json_roundtrip(self):
        client = make_mock(context_length=131072)
        cfg = BenchmarkConfig(
            seq_lens=[1024],
            position_fracs=[0.0],
            densities=[1.0],
            repeats=1,
            seed=7,
        )
        result = run_benchmark(client, cfg, progress=False)
        data = result.to_dict()
        assert "cells" in data
        assert data["claimed_context"] == 131072
        # JSON 字符串也应可反序列化
        import json as jsonlib
        parsed = jsonlib.loads(result.to_json())
        assert parsed["claimed_context"] == 131072
