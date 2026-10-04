"""Resume builder helpers: turn pasted resume text into structured fields, and sharpen bullets.

Templates and PDF export run in the browser (print to PDF), so the server only does the AI parts.
"""
from app import llm, market

PARSE_SYSTEM = """Extract the resume into structured fields. Copy facts exactly, do not invent anything.
Leave a field empty if it is missing. Return ONLY JSON:
{"name": str, "title": str, "email": str, "phone": str, "location": str, "links": [str],
 "summary": str,
 "experience": [{"role": str, "company": str, "dates": str, "bullets": [str]}],
 "education": [{"degree": str, "school": str, "dates": str}],
 "skills": [str],
 "projects": [{"name": str, "details": str}]}"""

POLISH_SYSTEM = """You are a senior resume writer. {market}
Rewrite each bullet to start with a strong action verb, name the tool or skill, and show impact.
Keep every fact true: never invent numbers, employers or tools. If a number is missing, leave a placeholder
like [X%] for the candidate to fill in. Keep each bullet under 28 words. Return ONLY JSON:
{{"bullets": [str]}}  (same count and order as the input)"""

SUMMARY_SYSTEM = """You write resume summaries. {market}
Write a 2-3 sentence professional summary for the target role using ONLY the facts given. No first person pronouns,
no clichés, no invented numbers. Return ONLY JSON: {{"summary": str}}"""

MAX_BULLETS = 12


def _s(v, n):
    return " ".join(str(v or "").split())[:n]


def _list(v, n, m):
    return [_s(x, m) for x in v if _s(x, m)][:n] if isinstance(v, list) else []


def _dicts(v, n):
    return [x for x in v if isinstance(x, dict)][:n] if isinstance(v, list) else []


def parse(text: str) -> dict:
    out = llm.chat_json("builder_parse", PARSE_SYSTEM, text[:12000], model=llm.FAST_MODEL)
    return {
        "name": _s(out.get("name"), 80), "title": _s(out.get("title"), 100), "email": _s(out.get("email"), 120),
        "phone": _s(out.get("phone"), 40), "location": _s(out.get("location"), 100),
        "links": _list(out.get("links"), 5, 200), "summary": _s(out.get("summary"), 700),
        "experience": [
            {"role": _s(e.get("role"), 100), "company": _s(e.get("company"), 100), "dates": _s(e.get("dates"), 40),
             "bullets": _list(e.get("bullets"), 10, 400)}
            for e in _dicts(out.get("experience"), 10)
        ],
        "education": [
            {"degree": _s(e.get("degree"), 120), "school": _s(e.get("school"), 120), "dates": _s(e.get("dates"), 40)}
            for e in _dicts(out.get("education"), 6)
        ],
        "skills": _list(out.get("skills"), 40, 50),
        "projects": [{"name": _s(p.get("name"), 100), "details": _s(p.get("details"), 400)} for p in _dicts(out.get("projects"), 6)],
    }


def polish(role: str, bullets: list[str], country: str) -> list[str]:
    bullets = [_s(b, 400) for b in bullets if _s(b, 400)][:MAX_BULLETS]
    if not bullets:
        raise ValueError("Add at least one bullet to improve.")
    out = llm.chat_json(
        "builder_polish", POLISH_SYSTEM.format(market=market.context(country)),
        f"TARGET ROLE: {_s(role, 100) or 'not given'}\nBULLETS:\n" + "\n".join(f"- {b}" for b in bullets),
        model=llm.FAST_MODEL,
    )
    res = _list(out.get("bullets"), MAX_BULLETS, 300)
    if len(res) != len(bullets):
        return bullets  # model broke the contract; never return misaligned text
    return res


def summary(role: str, facts: str, country: str) -> str:
    facts = _s(facts, 3000)
    if len(facts) < 20:
        raise ValueError("Add some experience or skills first so the summary has facts to use.")
    out = llm.chat_json(
        "builder_summary", SUMMARY_SYSTEM.format(market=market.context(country)),
        f"TARGET ROLE: {_s(role, 100) or 'not given'}\nFACTS:\n{facts}", model=llm.FAST_MODEL,
    )
    return _s(out.get("summary"), 700)
