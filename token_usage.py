from typing import Any


def extract_token_usage(response: Any) -> dict[str, int]:
    """
    Normalize token usage from LangChain/OpenAI responses.

    Returns a stable shape for UI aggregation:
    - input_tokens
    - output_tokens
    - total_tokens
    """
    usage = getattr(response, "usage_metadata", None) or {}
    if not usage and getattr(response, "response_metadata", None):
        usage = response.response_metadata.get("token_usage", {}) or {}

    input_tokens = (
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("input")
        or 0
    )
    output_tokens = (
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("output")
        or 0
    )
    total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens)

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens),
    }
