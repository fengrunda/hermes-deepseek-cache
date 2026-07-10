"""DeepSeek cache token parsing and per-session accumulation."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def parse_cache_tokens(hook_payload: dict) -> dict:
    """Extract DeepSeek cache hit/miss tokens from post_api_request hook payload.

    Hermes passes normalized CanonicalUsage (cache_read_tokens / input_tokens).
    Raw API fields (prompt_cache_hit_tokens) are kept as fallback only.
    """
    if (hook_payload.get("provider") or "").lower() != "deepseek":
        return {"hit_tokens": 0, "miss_tokens": 0}

    usage = hook_payload.get("usage")
    if not isinstance(usage, dict):
        return {"hit_tokens": 0, "miss_tokens": 0}

    hit = _to_int(
        usage.get("cache_read_tokens")
        or usage.get("prompt_cache_hit_tokens")
    )
    miss = _to_int(usage.get("prompt_cache_miss_tokens"))
    if miss == 0:
        # CanonicalUsage: uncached prompt portion lives in input_tokens.
        miss = _to_int(usage.get("input_tokens"))
    if miss == 0 and hit > 0:
        prompt = _to_int(usage.get("prompt_tokens"))
        if prompt > hit:
            miss = prompt - hit

    return {"hit_tokens": hit, "miss_tokens": miss}


def _to_int(value) -> int:
    try:
        return int(value) if value else 0
    except (TypeError, ValueError):
        return 0


def accumulate_stats(session_id: str, cache_data: dict, stats_path: Path) -> None:
    """Accumulate cache tokens per session into stats.json (atomic write)."""
    if not session_id:
        return

    stats_path.parent.mkdir(parents=True, exist_ok=True)

    stats = {}
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stats = {}

    entry = stats.get(session_id, {"hit_tokens": 0, "miss_tokens": 0})
    entry["hit_tokens"] = entry.get("hit_tokens", 0) + cache_data.get("hit_tokens", 0)
    entry["miss_tokens"] = entry.get("miss_tokens", 0) + cache_data.get("miss_tokens", 0)
    entry["last_updated"] = datetime.now(timezone.utc).isoformat()

    stats[session_id] = entry

    json_str = json.dumps(stats, ensure_ascii=False, indent=2)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=stats_path.parent,
        delete=False,
        encoding="utf-8",
    )
    try:
        tmp.write(json_str)
        tmp.close()
        os.replace(tmp.name, stats_path)
    except Exception:
        os.unlink(tmp.name)
        raise
