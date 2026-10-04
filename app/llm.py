"""LLM access through Nebius Token Factory (OpenAI-compatible API).

Two Nemotron models are used:
  * FAST_MODEL   - question generation and interviewer follow-ups
  * STRONG_MODEL - answer scoring, resume review and the final report

If NEBIUS_API_KEY is not set the app runs in MOCK mode with canned replies so the
UI and tests work offline. The mock is never used when a key is present.
"""
import json
import os
import re
import threading

BASE_URL = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
# Confirm exact IDs in the Token Factory model catalog and override via env.
FAST_MODEL = os.environ.get("FAST_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
STRONG_MODEL = os.environ.get("STRONG_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")


class LLMError(RuntimeError):
    """The model service failed or returned unusable output."""


# Cap simultaneous model calls so many users cannot exhaust the API rate limit.
_SLOTS = threading.BoundedSemaphore(int(os.environ.get("LLM_CONCURRENCY", "8")))


def mock_mode() -> bool:
    return not os.environ.get("NEBIUS_API_KEY")


def _client():
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"], timeout=90, max_retries=2)


def chat(messages, model: str = FAST_MODEL, **kw) -> str:
    try:
        with _SLOTS:
            resp = _client().chat.completions.create(model=model, messages=messages, **kw)
    except Exception as e:  # network, auth, rate limit, timeout
        raise LLMError(f"model call failed: {type(e).__name__}") from e
    return resp.choices[0].message.content or ""


def extract_json(text: str):
    """Pull the first JSON object out of a model reply (handles ``` fences and prose)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("no JSON object in model reply")
    return json.loads(m.group(0))


def chat_json(task: str, system: str, user: str, model: str = FAST_MODEL):
    """Ask for JSON; in mock mode return the canned reply for `task`."""
    if mock_mode():
        from app import mock

        return mock.reply(task, user)
    for attempt in range(2):
        out = chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=model,
            temperature=0.4,
        )
        try:
            return extract_json(out)
        except (ValueError, json.JSONDecodeError):
            user += "\n\nReturn ONLY one valid JSON object, nothing else."
    raise LLMError("model did not return valid JSON")
