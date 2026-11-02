"""客户端测试."""

import pytest

from effective_context_lab.clients import MockClient, get_client


class TestMockClient:
    def test_mock_returns_string(self):
        c = MockClient(model="m", base_url="http://localhost:9")
        c._expected_answer = "Paris"
        out = c.complete("What is X?")
        assert isinstance(out, str)

    def test_mock_tracks_calls(self):
        c = MockClient(model="m", base_url="http://localhost:9")
        c._expected_answer = "Paris"
        c.complete("hello")
        c.complete("world")
        assert c.calls == 2


class TestGetClient:
    def test_openai(self):
        c = get_client("model-x", kind="openai")
        assert c.model == "model-x"

    def test_mock(self):
        c = get_client("model-x", kind="mock")
        assert c.model == "model-x"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_client("x", kind="unknown")
