"""Interview prep pack: tailored questions WITH model answers from the candidate's own resume and JD.

Two Nano calls run in parallel (core questions, and coding questions when the profile is technical) and
the result is cached by input hash so repeat requests are instant.
"""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

from app import basic_in, llm, market

CORE_SYSTEM = """You are a senior interviewer and coach. {market}
Using ONLY the candidate's resume, target role and job description (if given), write exactly {spec}
questions for THIS candidate and role, easy to hard. For each, write a model answer the candidate could say, built from their
own experience (never invent employers, projects or numbers; if a detail is missing use a short placeholder like [X]).
Model answers: 3-5 sentences, spoken style, with STAR structure for behavioral ones.
Also set "coding": true if the role or resume is a software, data, QA-automation or other coding-heavy profile.
Return ONLY JSON:
{{"coding": bool, "focus": [str] (3-5 topics the JD stresses that they should revise),
 "questions": [{{"type": "technical|behavioral|scenario", "question": str, "model_answer": str, "why_asked": str (one short line)}}]}}"""

CODE_SYSTEM = """You are a coding interviewer. {market}
Write exactly 3 coding interview questions matched to this candidate's stack and the job description, easy to medium
to hard. For each give the problem statement with a small example, the key idea in words, and a clean solution in the
candidate's main language (Python if unclear), under 25 lines. Return ONLY JSON:
{{"coding_questions": [{{"title": str, "level": "easy|medium|hard", "problem": str, "approach": str, "solution": str, "language": str, "complexity": str}}]}}"""

_cache: dict[str, dict] = {}
_lock = threading.Lock()
_MAX = 200


def _s(v, n):
    return " ".join(str(v or "").split())[:n]


def _ctx(resume, role, jd):
    s = f"TARGET ROLE: {role}\n\nRESUME:\n{resume[:9000]}"
    if jd.strip():
        s += f"\n\nJOB DESCRIPTION:\n{jd[:5000]}"
    return s


SPECS = (
    "4 technical questions (about their real stack and the JD's requirements)",
    "2 behavioral questions and 2 scenario questions (client, deadline, conflict situations)",
)


def _core(resume, role, jd, country, spec):
    out = llm.chat_json("prep_core", CORE_SYSTEM.format(market=market.context(country), spec=spec), _ctx(resume, role, jd), model=llm.FAST_MODEL)
    qs = []
    for q in out.get("questions", [])[:10] if isinstance(out.get("questions"), list) else []:
        if isinstance(q, dict) and q.get("question"):
            qs.append({
                "type": q.get("type") if q.get("type") in ("technical", "behavioral", "scenario") else "technical",
                "question": _s(q["question"], 500),
                "model_answer": str(q.get("model_answer", ""))[:1800].strip(),
                "why_asked": _s(q.get("why_asked"), 200),
            })
    if not qs:
        raise llm.LLMError("no questions returned")
    focus = [_s(x, 80) for x in out.get("focus", [])][:5] if isinstance(out.get("focus"), list) else []
    return bool(out.get("coding")), focus, qs


def _code(resume, role, jd, country):
    out = llm.chat_json("prep_code", CODE_SYSTEM.format(market=market.context(country)), _ctx(resume, role, jd), model=llm.FAST_MODEL)
    res = []
    for q in out.get("coding_questions", [])[:3] if isinstance(out.get("coding_questions"), list) else []:
        if isinstance(q, dict) and q.get("problem"):
            res.append({
                "title": _s(q.get("title"), 120),
                "level": q.get("level") if q.get("level") in ("easy", "medium", "hard") else "medium",
                "problem": str(q["problem"])[:1200].strip(), "approach": str(q.get("approach", ""))[:900].strip(),
                "solution": str(q.get("solution", ""))[:2500].strip(), "language": _s(q.get("language"), 20) or "Python",
                "complexity": _s(q.get("complexity"), 80),
            })
    return res


def _key(prefix, resume, role, jd, country):
    return prefix + hashlib.sha256("\x00".join([market.normalize(country), role.strip().lower(), resume.strip(), jd.strip()]).encode()).hexdigest()


def _get(key):
    with _lock:
        return _cache.get(key)


def _put(key, val):
    with _lock:
        if len(_cache) >= _MAX:
            _cache.clear()
        _cache[key] = val


def build(resume: str, role: str, jd: str, country: str) -> dict:
    """Core pack: two parallel Nano calls (technical / behavioral+scenario). Coding questions load separately."""
    if market.is_basic_in(country, resume, role, "auto"):
        # India, 10th/12th/any graduate: the reviewed question set with sample answers (no AI call, never cached so repeat visits vary)
        picked = basic_in.pick(10, role, jd)
        return {
            "country": "India", "coding_profile": False, "basic": True,
            "focus": ["Tell me about yourself in English", "Why this job", "Customer handling", "Shifts and attitude", "Basic computer and typing"],
            "questions": [
                {"type": q["type"], "question": q["question"], "model_answer": q["ref"], "why_asked": _s(q["tip"], 200) or "Asked in most entry-level interviews in India."}
                for q in picked
            ],
        }
    key = _key("core:", resume, role, jd, country)
    if (hit := _get(key)) is not None:
        return hit
    with ThreadPoolExecutor(max_workers=2) as ex:
        fa, fb = (ex.submit(_core, resume, role, jd, country, sp) for sp in SPECS)
        try:
            ca, focus, qa = fa.result()
        except llm.LLMError:
            ca, focus, qa = False, [], []
        try:
            cb, focus_b, qb = fb.result()
        except llm.LLMError:
            cb, focus_b, qb = False, [], []
    qs = qa + qb
    if not qs:
        raise llm.LLMError("no questions returned")
    res = {"country": market.normalize(country), "coding_profile": bool(ca or cb or market.looks_technical(role, resume)),
           "focus": (focus or focus_b)[:5], "questions": qs}
    _put(key, res)
    return res


def build_coding(resume: str, role: str, jd: str, country: str) -> dict:
    key = _key("code:", resume, role, jd, country)
    if (hit := _get(key)) is not None:
        return hit
    res = {"coding_questions": _code(resume, role, jd, country)}
    _put(key, res)
    return res
