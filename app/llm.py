"""Nebius Token Factory client (OpenAI-compatible API)."""
import os

from openai import OpenAI

BASE_URL = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
# Model IDs are confirmed against the Token Factory catalog; override via env.
FAST_MODEL = os.environ.get("FAST_MODEL", "nvidia/nemotron-fast-placeholder")
STRONG_MODEL = os.environ.get("STRONG_MODEL", "nvidia/nemotron-ultra-placeholder")


def client() -> OpenAI:
    return OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"])


def chat(messages, model: str = FAST_MODEL, **kw) -> str:
    resp = client().chat.completions.create(model=model, messages=messages, **kw)
    return resp.choices[0].message.content
