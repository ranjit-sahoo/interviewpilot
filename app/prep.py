"""Interview prep pack: tailored questions WITH model answers from the candidate's own resume and JD.

Two Nano calls run in parallel (core questions, and coding questions when the profile is technical) and
the result is cached by input hash so repeat requests are instant.
"""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

from app import llm, market

CORE_SYSTEM = """You are a senior interviewer and coach. {market}
Using ONLY the candidate's resume, target role and job description (if given), write exactly 8 likely interview
questions for THIS candidate and role: 4 technical (about their real stack and the JD's requirements), 2 behavioral
and 2 scenario questions. Order easy to hard. For each, write a model answer the candidate could say, built from their
own experience (never invent employers, projects or numbers; if a detail is missing use a short placeholder like [X]).
Model answers: 3-6 sentences, spoken style, with STAR structure for behavioral ones.
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


def _core(resume, role, jd, country):
    out = llm.chat_json("prep_core", CORE_SYSTEM.format(market=market.context(country)), _ctx(resume, role, jd), model=llm.FAST_MODEL)
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


def build(resume: str, role: str, jd: str, country: str) -> dict:
    key = hashlib.sha256("\x00".join([market.normalize(country), role.strip().lower(), resume.strip(), jd.strip()]).encode()).hexdigest()
    with _lock:
        if key in _cache:
            return _cache[key]
    # Start the coding call in parallel only when the resume/role looks technical, to avoid wasted spend.
    maybe_code = market.looks_technical(role, resume)
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_core = ex.submit(_core, resume, role, jd, country)
        f_code = ex.submit(_code, resume, role, jd, country) if maybe_code else None
        coding, focus, qs = f_core.result()
        code_qs = []
        if f_code is not None:
            try:
                code_qs = f_code.result()
            except llm.LLMError:
                code_qs = []  # the core pack is still useful
    res = {"country": market.normalize(country), "coding_profile": coding or bool(code_qs), "focus": focus,
           "questions": qs, "coding_questions": code_qs if (coding or code_qs) else []}
    with _lock:
        if len(_cache) >= _MAX:
            _cache.clear()
        _cache[key] = res
    return res
