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


# Hard daily ceiling on model calls for the whole app (spend protection). Resets at UTC midnight.
DAILY_CAP = int(os.environ.get("LLM_DAILY_CAP", "4000"))
_day = {"d": None, "n": 0}
_day_lock = threading.Lock()


def _budget():
    import time

    today = time.strftime("%Y-%m-%d", time.gmtime())
    with _day_lock:
        if _day["d"] != today:
            _day["d"], _day["n"] = today, 0
        if _day["n"] >= DAILY_CAP:
            raise LLMError("daily model budget reached")
        _day["n"] += 1


def calls_today() -> int:
    return _day["n"]


def mock_mode() -> bool:
    return not os.environ.get("NEBIUS_API_KEY")


def _client():
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"], timeout=90, max_retries=2)


def chat(messages, model: str = FAST_MODEL, **kw) -> str:
    _budget()
    from app import spend

    try:
        spend.check()
    except spend.BudgetExceeded as e:
        raise LLMError("budget") from e
    kw.setdefault("max_tokens", int(os.environ.get("LLM_MAX_TOKENS", "8000")))
    if model == FAST_MODEL and os.environ.get("FAST_THINKING") != "1":
        # Nano can spend 30+ seconds "thinking" before a short JSON answer. Turning it off is about 20x faster.
        kw = {**kw, "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}
    try:
        with _SLOTS:
            resp = _client().chat.completions.create(model=model, messages=messages, **kw)
    except Exception as e:  # network, auth, rate limit, timeout
        if "extra_body" in kw and getattr(e, "status_code", None) == 400:
            kw = {k: v for k, v in kw.items() if k != "extra_body"}
            try:
                with _SLOTS:
                    resp = _client().chat.completions.create(model=model, messages=messages, **kw)
            except Exception as e2:
                raise LLMError(f"model call failed: {type(e2).__name__}") from e2
        else:
            raise LLMError(f"model call failed: {type(e).__name__}") from e
    out = resp.choices[0].message.content or ""
    try:
        u = resp.usage
        tin, tout = (u.prompt_tokens or 0), (u.completion_tokens or 0)
    except Exception:  # no usage reported: assume a generous size so the guard still counts
        tin, tout = sum(len(m["content"]) for m in messages) // 3, max(len(out) // 3, 1500)
    spend.record(spend.cost(model == STRONG_MODEL, tin, tout))
    return out


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
