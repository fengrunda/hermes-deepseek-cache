"""Unit tests for usage.py: cache token parsing + per-session accumulation."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from usage import accumulate_stats, parse_cache_tokens


# ── parse_cache_tokens ────────────────────────────────────────────


class TestParseCacheTokens:
    """hit/miss 解析 / 空 usage / 非 DeepSeek."""

    def test_parses_canonical_usage(self):
        payload = {
            "provider": "deepseek",
            "usage": {
                "cache_read_tokens": 100,
                "input_tokens": 50,
                "prompt_tokens": 150,
            },
        }
        result = parse_cache_tokens(payload)
        assert result == {"hit_tokens": 100, "miss_tokens": 50}

    def test_parses_raw_deepseek_fields(self):
        payload = {
            "provider": "deepseek",
            "usage": {
                "prompt_cache_hit_tokens": 100,
                "prompt_cache_miss_tokens": 50,
            },
        }
        result = parse_cache_tokens(payload)
        assert result == {"hit_tokens": 100, "miss_tokens": 50}

    def test_derives_miss_from_prompt_minus_hit(self):
        payload = {
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "usage": {
                "cache_read_tokens": 800,
                "prompt_tokens": 1000,
            },
        }
        result = parse_cache_tokens(payload)
        assert result == {"hit_tokens": 800, "miss_tokens": 200}

    def test_empty_usage_returns_zeros(self):
        result = parse_cache_tokens({"provider": "deepseek", "usage": {}})
        assert result == {"hit_tokens": 0, "miss_tokens": 0}

    def test_non_deepseek_returns_zeros(self):
        result = parse_cache_tokens({"provider": "openai", "usage": {"prompt_cache_hit_tokens": 100}})
        assert result == {"hit_tokens": 0, "miss_tokens": 0}

    def test_deepseek_model_name_without_provider_returns_zeros(self):
        result = parse_cache_tokens({
            "provider": "openrouter",
            "model": "deepseek/deepseek-v4-pro",
            "usage": {"cache_read_tokens": 100, "input_tokens": 10},
        })
        assert result == {"hit_tokens": 0, "miss_tokens": 0}

    def test_missing_usage_key_returns_zeros(self):
        result = parse_cache_tokens({"provider": "deepseek"})
        assert result == {"hit_tokens": 0, "miss_tokens": 0}

# ── accumulate_stats ──────────────────────────────────────────────


class TestAccumulateStats:
    """stats 累计 / 损坏恢复 / 目录创建."""

    def test_new_session_writes_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "stats.json"
            accumulate_stats("sess-1", {"hit_tokens": 10, "miss_tokens": 5}, stats_path)

            assert stats_path.exists()
            data = json.loads(stats_path.read_text())
            assert "sess-1" in data
            assert data["sess-1"]["hit_tokens"] == 10
            assert data["sess-1"]["miss_tokens"] == 5
            assert "last_updated" in data["sess-1"]

    def test_accumulates_existing_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "stats.json"
            accumulate_stats("sess-1", {"hit_tokens": 10, "miss_tokens": 5}, stats_path)
            accumulate_stats("sess-1", {"hit_tokens": 3, "miss_tokens": 2}, stats_path)

            data = json.loads(stats_path.read_text())
            assert data["sess-1"]["hit_tokens"] == 13
            assert data["sess-1"]["miss_tokens"] == 7

    def test_multiple_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "stats.json"
            accumulate_stats("sess-1", {"hit_tokens": 10, "miss_tokens": 5}, stats_path)
            accumulate_stats("sess-2", {"hit_tokens": 20, "miss_tokens": 0}, stats_path)

            data = json.loads(stats_path.read_text())
            assert data["sess-1"]["hit_tokens"] == 10
            assert data["sess-2"]["hit_tokens"] == 20
            assert data["sess-2"]["miss_tokens"] == 0

    def test_corrupted_stats_json_resets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "stats.json"
            stats_path.write_text("not valid json {{{")

            # should not crash, reset and write fresh stats
            accumulate_stats("sess-1", {"hit_tokens": 5, "miss_tokens": 0}, stats_path)
            data = json.loads(stats_path.read_text())
            assert data["sess-1"]["hit_tokens"] == 5

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "deep" / "nested" / "stats.json"
            accumulate_stats("sess-1", {"hit_tokens": 1, "miss_tokens": 0}, stats_path)

            assert stats_path.exists()

    def test_empty_cache_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "stats.json"
            accumulate_stats("sess-1", {}, stats_path)

            data = json.loads(stats_path.read_text())
            assert data["sess-1"]["hit_tokens"] == 0
            assert data["sess-1"]["miss_tokens"] == 0

    def test_skips_empty_session_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_path = Path(tmpdir) / "stats.json"
            accumulate_stats("", {"hit_tokens": 10, "miss_tokens": 5}, stats_path)
            assert not stats_path.exists()
