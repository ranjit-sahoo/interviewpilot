"""One-page company research brief, adapted to the candidate's country. Cached; uses the fast model."""
import threading
from urllib.parse import quote

from app import companies, llm, market, prompts, singleflight

_cache: dict[tuple, dict] = {}
_lock = threading.Lock()
_MAX = 300


def _clean(s, n):
    return " ".join(str(s or "").split())[:n]


def _list(v, n=5, w=300):
    return [_clean(x, w) for x in (v if isinstance(v, list) else []) if _clean(x, w)][:n]


def _build_uncached(company: str, role: str, country: str) -> dict:
    company, role = _clean(company, 80), _clean(role, 120) or "the role"
    country = market.normalize(country)
    key = (company.lower(), role.lower(), country)
    with _lock:
        if key in _cache:
            return _cache[key]
    prof = companies.find(company, country)
    known = ""
    if prof:
        known = (f"Known public pattern (use it): kind {prof['kind']}; typical rounds: {prof['rounds']}; "
                 f"focus: {', '.join(prof['focus'])}.")
    out = llm.chat_json(
        "brief", prompts.BRIEF_SYSTEM.format(market=market.context(country), company=company, role=role, known=known),
        f"Company: {company}\nRole: {role}\nCandidate market: {country}", model=llm.FAST_MODEL,
    )
    if not isinstance(out, dict) or not out.get("summary"):
        raise llm.LLMError("no brief")
    res = {
        "company": company, "role": role, "country": country, "known_profile": bool(prof),
        "summary": _clean(out.get("summary"), 900), "market_note": _clean(out.get("market_note"), 700),
        "recent_focus": _list(out.get("recent_focus"), 4), "culture": _list(out.get("culture"), 4),
        "process": _list(out.get("process"), 7), "question_style": _list(out.get("question_style"), 5),
        "why_join": _clean(out.get("why_join"), 800), "ask_them": _list(out.get("ask_them"), 4),
        "watch_out": _list(out.get("watch_out"), 3),
        "caution": _clean(out.get("caution"), 300) or "Verify recent news on the company's own newsroom before the interview.",
        "news_url": "https://news.google.com/search?q=" + quote(company + " company"),
    }
    with _lock:
        if len(_cache) >= _MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = res
    return res


def build(company: str, role: str, country: str) -> dict:
    """Same company, role and country at the same moment share one AI call."""
    k = (_clean(company, 80).lower(), (_clean(role, 120) or "the role").lower(), market.normalize(country))
    with singleflight.lock(("brief",) + k):
        return _build_uncached(company, role, country)
