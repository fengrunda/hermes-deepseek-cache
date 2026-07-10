"""Unit tests for wire.py: DeepSeek detection + reasoning_content strip."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from wire import is_deepseek_target, on_llm_request, shape_messages_for_deepseek


class TestIsDeepSeekTarget:
    def test_provider_deepseek(self):
        assert is_deepseek_target("deepseek") is True
        assert is_deepseek_target("DeepSeek") is True

    def test_other_provider_no_match_even_with_deepseek_model(self):
        assert is_deepseek_target("openai") is False
        assert is_deepseek_target("openrouter") is False
        assert is_deepseek_target("alibaba") is False
        assert is_deepseek_target("custom") is False


class TestShapeMessagesForDeepSeek:
    def test_strips_reasoning_content_and_reasoning(self):
        msgs = [
            {"role": "assistant", "content": "hi", "reasoning_content": " ", "reasoning": "trace"},
        ]
        shaped, count = shape_messages_for_deepseek(msgs)
        assert count == 1
        assert shaped[0] == {"role": "assistant", "content": "hi"}

    def test_preserves_tool_calls_reasoning(self):
        msgs = [
            {
                "role": "assistant",
                "tool_calls": [{"id": "t1"}],
                "reasoning_content": "thinking...",
                "reasoning": "also here",
            },
        ]
        shaped, count = shape_messages_for_deepseek(msgs)
        assert count == 0
        assert shaped == msgs


def make_request(messages):
    return {"model": "deepseek-v3", "messages": messages}


class TestOnLlmRequest:
    def test_non_deepseek_returns_none(self):
        result = on_llm_request(
            provider="openai",
            model="deepseek-v3",
            request={
                "model": "deepseek-v3",
                "messages": [{"role": "assistant", "content": "hi", "reasoning_content": "x"}],
            },
        )
        assert result is None

    def test_custom_provider_with_deepseek_base_url_returns_none(self):
        result = on_llm_request(
            provider="custom",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/v1",
            request={"messages": [{"role": "assistant", "content": "hi", "reasoning_content": "x"}]},
        )
        assert result is None

    def test_no_op_returns_none(self):
        msgs = [{"role": "assistant", "content": "hi"}]
        result = on_llm_request(
            provider="deepseek",
            model="deepseek-v3",
            request=make_request(msgs),
        )
        assert result is None

    def test_strips_reasoning_content_from_assistant(self):
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi", "reasoning_content": "thinking..."},
        ]
        result = on_llm_request(provider="deepseek", model="deepseek-v3", request=make_request(msgs))
        assert result is not None
        assert result["source"] == "hermes-deepseek-cache"
        assert "stripped reasoning echo" in result["reason"]
        assert "reasoning_content" not in result["request"]["messages"][1]

    def test_strips_space_pad_from_plain_assistant(self):
        msgs = [{"role": "assistant", "content": "hi", "reasoning_content": " "}]
        result = on_llm_request(provider="deepseek", model="deepseek-v3", request=make_request(msgs))
        assert result is not None
        assert "reasoning_content" not in result["request"]["messages"][0]

    def test_preserves_tool_calls(self):
        msgs = [
            {"role": "assistant", "tool_calls": [{"id": "t1"}], "reasoning_content": "thinking..."},
        ]
        result = on_llm_request(provider="deepseek", model="deepseek-v3", request=make_request(msgs))
        assert result is None
