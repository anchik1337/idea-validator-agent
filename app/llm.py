"""
Thin wrapper around the Anthropic SDK.

Two production concerns handled here:
  1. Retries with exponential backoff for transient errors (overload, rate limits,
     network blips). Real systems fail sometimes; a good engineer plans for it.
  2. A helper that FORCES a specific tool so we always get structured output.

Interview line: "Every model call goes through one wrapper with retry/backoff, so
failure handling lives in one place instead of being copy-pasted everywhere."
"""

import time
import anthropic

from .config import MAX_RETRIES, RETRY_BASE_DELAY, MAX_TOKENS

# The SDK reads ANTHROPIC_API_KEY from the environment automatically.
client = anthropic.Anthropic()


def _call_with_retries(**kwargs):
    """Call the Messages API, retrying transient failures with exponential backoff."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.messages.create(**kwargs)
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            # 4xx that are our fault (e.g. bad request) should not be retried blindly,
            # but overloaded/rate-limit/5xx are worth retrying.
            status = getattr(e, "status_code", None)
            if status in (400, 401, 403, 404):
                raise
            last_error = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[llm] transient error ({status}); retry {attempt + 1}/{MAX_RETRIES} in {delay}s")
            time.sleep(delay)
    raise last_error


def get_structured(model: str, prompt: str, tool: dict) -> dict:
    """
    Ask the model and force it to answer by "calling" `tool`.
    Returns the tool input (a dict matching tool['input_schema']).

    tool_choice forces the model to use exactly this tool, which is how we
    guarantee a structured JSON answer instead of free text.
    """
    resp = _call_with_retries(
        model=model,
        max_tokens=MAX_TOKENS,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == tool["name"]:
            return block.input
    raise ValueError("Model did not return the expected tool call.")


def raw_message(model: str, messages: list, tools=None):
    """A plain message call (used by the agentic research loop)."""
    kwargs = {"model": model, "max_tokens": MAX_TOKENS, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    return _call_with_retries(**kwargs)
