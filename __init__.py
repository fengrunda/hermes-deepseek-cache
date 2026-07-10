from pathlib import Path

from .usage import accumulate_stats, parse_cache_tokens
from .wire import on_llm_request


def register(ctx) -> None:
    ctx.register_middleware("llm_request", on_llm_request)
    ctx.register_hook("post_api_request", on_post_api_request)


def on_post_api_request(**kwargs) -> None:
    cache_data = parse_cache_tokens(kwargs)
    stats_path = Path.home() / ".hermes" / "plugins" / "hermes-deepseek-cache" / "stats.json"
    accumulate_stats(kwargs.get("session_id", ""), cache_data, stats_path)
