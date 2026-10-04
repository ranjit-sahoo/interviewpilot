"""STAR answer builder: turns a rough real experience into a polished Situation-Task-Action-Result answer."""
from app import llm, market, prompts


def _clean(s, n):
    return " ".join(str(s or "").split())[:n]


def _list(v, n=5, w=300):
    return [_clean(x, w) for x in (v if isinstance(v, list) else []) if _clean(x, w)][:n]


def build(experience: str, question: str, role: str, country: str) -> dict:
    exp = (experience or "").strip()[:4000]
    user = f"TARGET ROLE: {_clean(role, 120) or 'not stated'}\n"
    if question.strip():
        user += f"INTERVIEW QUESTION TO ANSWER: {_clean(question, 300)}\n"
    user += f"\nCANDIDATE'S ROUGH EXPERIENCE:\n{exp}"
    out = llm.chat_json("star", prompts.STAR_SYSTEM.format(market=market.context(country)), user, model=llm.FAST_MODEL)
    if not isinstance(out, dict) or not out.get("spoken_answer"):
        raise llm.LLMError("no STAR answer")
    return {
        "situation": _clean(out.get("situation"), 700), "task": _clean(out.get("task"), 700),
        "action": _clean(out.get("action"), 1200), "result": _clean(out.get("result"), 700),
        "spoken_answer": " ".join(str(out["spoken_answer"]).split())[:2500],
        "opener": _clean(out.get("opener"), 300),
        "missing": _list(out.get("missing")), "tips": _list(out.get("tips"), 4),
    }
