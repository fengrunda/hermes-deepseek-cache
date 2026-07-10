"""DeepSeek detection + reasoning wire shaping (Reasonix-style)."""

# Wire-only fields that must not appear on plain assistant turns for DeepSeek.
# Tool-call turns keep reasoning_content (API requirement).
_PLAIN_ASSISTANT_STRIP_KEYS = (
    "reasoning_content",
    "reasoning",
    "reasoning_details",
)


def is_deepseek_target(provider: str) -> bool:
    """仅当 Hermes provider 为 deepseek 时介入。"""
    return (provider or "").lower() == "deepseek"


def _has_tool_calls(msg: dict) -> bool:
    tool_calls = msg.get("tool_calls")
    return isinstance(tool_calls, list) and len(tool_calls) > 0


def shape_messages_for_deepseek(messages: list) -> tuple[list, int]:
    """Strip reasoning echo from plain assistant turns. Returns (messages, stripped_count)."""
    shaped: list = []
    stripped = 0

    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            shaped.append(msg)
            continue
        if _has_tool_calls(msg):
            shaped.append(msg)
            continue

        remove_keys = [k for k in _PLAIN_ASSISTANT_STRIP_KEYS if k in msg]
        if not remove_keys:
            shaped.append(msg)
            continue

        new_msg = {k: v for k, v in msg.items() if k not in remove_keys}
        shaped.append(new_msg)
        stripped += 1

    return shaped, stripped


def on_llm_request(**kwargs) -> dict | None:
    """llm_request middleware hook."""
    if not is_deepseek_target(kwargs.get("provider", "")):
        return None

    request = kwargs.get("request")
    if not isinstance(request, dict) or "messages" not in request:
        return None

    messages = request.get("messages")
    if not isinstance(messages, list):
        return None

    shaped, stripped = shape_messages_for_deepseek(messages)
    if stripped == 0:
        return None

    new_request = {**request, "messages": shaped}
    return {
        "request": new_request,
        "source": "hermes-deepseek-cache",
        "reason": f"stripped reasoning echo from {stripped} plain assistant turn(s)",
    }
