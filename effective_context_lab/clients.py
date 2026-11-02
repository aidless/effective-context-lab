"""模型客户端：OpenAI 兼容 (Magpie 1M 网关) 与 mock.

支持:
- OpenAICompatClient: 真实请求 Magpie 网关 (OpenAI 兼容 chat completions)
- MockClient: 确定性 mock (测试用), 可按位置/长度模拟准确率衰减
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field


@dataclass
class ModelClient:
    """模型客户端基类."""

    model: str
    base_url: str = "http://127.0.0.1:3425/v1"
    api_key: str = ""
    timeout: float = 120.0
    temperature: float = 0.0
    max_tokens: int = 32
    context_length: int = 0
    """模型声称的上下文窗口 (token)."""
    max_retries: int = 2
    retry_backoff: float = 1.0

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """发送补全请求，返回模型输出文本."""
        raise NotImplementedError

    def complete_full(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """发送补全请求，返回完整响应 (含 usage).

        Returns:
            dict: {
                "content": str,
                "prompt_tokens": int,
                "completion_tokens": int,
                "finish_reason": str | None,
            }
        """
        content = self.complete(
            prompt, system=system, max_tokens=max_tokens
        )
        return {
            "content": content,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "finish_reason": None,
        }


@dataclass
class OpenAICompatClient(ModelClient):
    """OpenAI 兼容客户端 (Magpie 网关)."""

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                if "choices" not in body or not body["choices"]:
                    raise RuntimeError(f"Bad response: {json.dumps(body)[:200]}")
                content = body["choices"][0]["message"].get("content", "")
                # GLM 等 reasoning 模型: content 可能为空而 reasoning_content 有内容.
                # 若 max_tokens 耗在 reasoning 上, content 为空, 尝试用 reasoning_content 尾部?
                # 不自动拼接 - 保持原语义, 空 content 由调用方处理.
                return content
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (attempt + 1))
        raise RuntimeError(f"Request failed after {self.max_retries + 1} attempts: {last_err}")

    def complete_full(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """发送补全请求，返回完整响应 (含 usage)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                if "choices" not in body or not body["choices"]:
                    raise RuntimeError(f"Bad response: {json.dumps(body)[:200]}")
                choice = body["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                usage = body.get("usage", {})
                return {
                    "content": content,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "finish_reason": choice.get("finish_reason"),
                }
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (attempt + 1))
        raise RuntimeError(f"Request failed after {self.max_retries + 1} attempts: {last_err}")


@dataclass
class MockClient(ModelClient):
    """确定性 mock 客户端.

    模拟 RULER 式衰减: 准确率 = f(seq_len, position_frac).
    用于测试 runner / scoring 而不烧真实 API.

    默认衰减模型 (对齐九号章节实测):
      - 位置 0 (最前) 保留 ~0.88
      - 位置 0.5 (中间) 保留 ~0.54 (Lost in the Middle)
      - 位置 1 (最后) 保留 ~0.63
      - 长度越长, 整体衰减越多 (窗口大 ≠ 能用)
    """

    def __post_init__(self):
        self.calls = 0
        self.last_prompt_len = 0

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.calls += 1
        self.last_prompt_len = len(prompt)

        # 从 prompt 中提取"期望答案" (探针格式: "What is X?" 期望 X 的 value)
        # 简单启发: 找 "is <expected>" 模式
        # 实际测试中通过 MockClient 配置期望答案
        if hasattr(self, "_expected_answer"):
            # 模拟衰减
            import random

            rng = random.Random(self.calls)
            # 基础准确率随长度衰减
            base = 0.95
            seq_factor = max(0.0, 1.0 - (self.last_prompt_len / 2000000.0))
            # 位置因子 (中间最差)
            pos_factor = 1.0
            if hasattr(self, "_position_frac"):
                pf = self._position_frac
                if 0.3 <= pf <= 0.7:
                    pos_factor = 0.6  # 中间
                elif pf < 0.2:
                    pos_factor = 0.95  # 最前
                else:
                    pos_factor = 0.75  # 最后
            accuracy = base * seq_factor * pos_factor
            if rng.random() < accuracy:
                return self._expected_answer
            return "I don't know"
        return "I don't know"


def get_client(
    model: str,
    *,
    kind: str = "openai",
    base_url: str = "http://127.0.0.1:3425/v1",
    **kwargs,
) -> ModelClient:
    """工厂函数创建客户端."""
    if kind == "openai":
        return OpenAICompatClient(model=model, base_url=base_url, **kwargs)
    if kind == "mock":
        return MockClient(model=model, base_url=base_url, **kwargs)
    raise ValueError(f"Unknown client kind: {kind}")
