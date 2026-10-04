import threading
from concurrent.futures import ThreadPoolExecutor

from app import comms, db, llm, market, prompts

MAX_RESUME_CHARS = 12000
MAX_JD_CHARS = 6000
N_QUESTIONS = 5
MAX_CANDIDATES = 10
MAX_NEGO_TURNS = 8

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock(sid: str) -> threading.Lock:
    with _locks_guard:
        if len(_locks) > 5000:
            _locks.clear()
        return _locks.setdefault(sid, threading.Lock())


def _ctx(resume: str, role: str, jd: str = "") -> str:
    s = f"TARGET ROLE: {role}\n\nRESUME:\n{resume[:MAX_RESUME_CHARS]}"
    if jd.strip():
        s += f"\n\nJOB DESCRIPTION:\n{jd[:MAX_JD_CHARS]}"
    return s


def _sys(template: str, country: str, **kw) -> str:
    return template.format(market=market.context(country), **kw)


# ---------- country ----------
def detect_country(resume: str, jd: str = "") -> dict:
    heur = market.detect_heuristic(resume, jd)
    if llm.mock_mode():
        return heur
    try:
        out = llm.chat_json(
            "detect", prompts.DETECT_SYSTEM, f"RESUME:\n{resume[:4000]}\n\nJOB DESCRIPTION:\n{jd[:2000]}", model=llm.FAST_MODEL
        )
        return {
            "country": market.normalize(out.get("country")),
            "confidence": out.get("confidence", "medium"),
            "reason": str(out.get("reason", ""))[:300],
        }
    except llm.LLMError:
        return heur  # detection is a convenience; never block the user on it


# ---------- resume + JD ----------
def review_resume(resume: str, role: str, jd: str = "", country: str = "US"):
    return llm.chat_json(
        "resume_review", _sys(prompts.RESUME_SYSTEM, country), _ctx(resume, role, jd), model=llm.STRONG_MODEL
    )


def match_jd(resume: str, role: str, jd: str, country: str = "US"):
    return llm.chat_json("match", _sys(prompts.MATCH_SYSTEM, country), _ctx(resume, role, jd), model=llm.STRONG_MODEL)


# ---------- mock interview ----------
def start_session(resume: str, role: str, jd: str = "", country: str = "US") -> dict:
    country = market.normalize(country)
    qs = llm.chat_json(
        "questions", _sys(prompts.QUESTIONS_SYSTEM, country, n=N_QUESTIONS), _ctx(resume, role, jd), model=llm.FAST_MODEL
    ).get("questions", [])[:N_QUESTIONS]
    if not qs:
        raise llm.LLMError("no questions generated")
    data = {
        "kind": "interview", "country": country, "resume": resume[:MAX_RESUME_CHARS], "role": role, "jd": jd[:MAX_JD_CHARS],
        "questions": qs, "index": 0, "turns": [], "done": False,
    }
    sid = db.create(data)
    return {"session_id": sid, "question": qs[0], "number": 1, "total": len(qs), "country": country}


def _interview(sid: str) -> dict:
    s = db.load(sid)
    if s is None or s.get("kind") != "interview":
        raise KeyError(sid)
    return s


def answer(sid: str, text: str) -> dict:
    with _lock(sid):
        s = _interview(sid)
        if s["done"]:
            raise ValueError("session already finished")
        q = s["questions"][s["index"]]
        user = f"{_ctx(s['resume'], s['role'], s['jd'])}\n\nQUESTION ({q['type']}): {q['question']}\n\nCANDIDATE ANSWER:\n{text[:4000]}"
        fb = llm.chat_json("turn", _sys(prompts.TURN_SYSTEM, s["country"]), user, model=llm.STRONG_MODEL)
        fb.setdefault("communication", {})
        fb["communication"]["metrics"] = comms.analyze(text)
        s["turns"].append({"question": q, "answer": text, "feedback": fb})
        s["index"] += 1
        finished = s["index"] >= len(s["questions"])
        s["done"] = finished
        db.save(sid, s)
    out = {"feedback": fb, "finished": finished}
    if not finished:
        out["next_question"] = s["questions"][s["index"]]
        out["number"] = s["index"] + 1
        out["total"] = len(s["questions"])
    return out


def report(sid: str) -> dict:
    with _lock(sid):
        s = _interview(sid)
        if "report" in s:
            return s["report"]
        if not s["turns"]:
            raise ValueError("answer at least one question first")
        transcript = "\n\n".join(
            f"Q ({t['question']['type']}): {t['question']['question']}\nA: {t['answer']}\n"
            f"Scores: {t['feedback'].get('scores')}\nFeedback: {t['feedback'].get('feedback')}\n"
            f"Speech metrics: {t['feedback']['communication'].get('metrics')}"
            for t in s["turns"]
        )
        rep = llm.chat_json(
            "report", _sys(prompts.REPORT_SYSTEM, s["country"]), f"ROLE: {s['role']}\n\n{transcript}", model=llm.STRONG_MODEL
        )
        s["report"] = rep
        db.save(sid, s)
        return rep


# ---------- salary negotiation ----------
def start_negotiation(resume: str, role: str, country: str = "US", current: str = "") -> dict:
    country = market.normalize(country)
    user = _ctx(resume, role) + (f"\n\nCANDIDATE CURRENT/EXPECTED PAY (as stated): {current[:200]}" if current.strip() else "")
    sc = llm.chat_json("nego_start", _sys(prompts.NEGO_START_SYSTEM, country), user, model=llm.STRONG_MODEL)
    data = {
        "kind": "negotiation", "country": country, "role": role, "scenario": sc, "turns": [], "done": False,
        "transcript": [{"who": "recruiter", "text": sc.get("opening_message", "")}],
    }
    sid = db.create(data)
    return {"session_id": sid, "scenario": sc, "country": country}


def _nego(sid: str) -> dict:
    s = db.load(sid)
    if s is None or s.get("kind") != "negotiation":
        raise KeyError(sid)
    return s


def negotiate(sid: str, message: str) -> dict:
    with _lock(sid):
        s = _nego(sid)
        if s["done"]:
            raise ValueError("negotiation already finished")
        s["transcript"].append({"who": "candidate", "text": message[:1500]})
        convo = "\n".join(f"{t['who'].upper()}: {t['text']}" for t in s["transcript"])
        out = llm.chat_json(
            "nego_turn",
            _sys(prompts.NEGO_TURN_SYSTEM, s["country"], scenario=str(s["scenario"])),
            f"ROLE: {s['role']}\n\n{convo}",
            model=llm.FAST_MODEL,
        )
        s["transcript"].append({"who": "recruiter", "text": out.get("recruiter_reply", "")})
        n = sum(1 for t in s["transcript"] if t["who"] == "candidate")
        s["done"] = bool(out.get("deal_closed")) or n >= MAX_NEGO_TURNS
        db.save(sid, s)
    return {**out, "finished": s["done"], "turn": n, "max_turns": MAX_NEGO_TURNS}


def negotiation_report(sid: str) -> dict:
    with _lock(sid):
        s = _nego(sid)
        if "report" in s:
            return s["report"]
        if not any(t["who"] == "candidate" for t in s["transcript"]):
            raise ValueError("say something to the recruiter first")
        convo = "\n".join(f"{t['who'].upper()}: {t['text']}" for t in s["transcript"])
        rep = llm.chat_json(
            "nego_report", _sys(prompts.NEGO_REPORT_SYSTEM, s["country"]), f"SCENARIO: {s['scenario']}\n\n{convo}",
            model=llm.STRONG_MODEL,
        )
        s["report"] = rep
        s["done"] = True
        db.save(sid, s)
        return rep


# ---------- recruiter screening ----------
def _screen_one(cand: dict, role: str, jd: str, country: str) -> dict:
    name = (cand.get("name") or "Candidate").strip()[:80]
    try:
        r = llm.chat_json(
            "recruiter", _sys(prompts.RECRUITER_SYSTEM, country), _ctx(cand["resume"], role, jd), model=llm.FAST_MODEL
        )
        r["score"] = max(0, min(100, int(r.get("score", 0))))
        return {"name": name, "ok": True, **r}
    except (llm.LLMError, ValueError, TypeError):
        return {"name": name, "ok": False, "error": "Could not screen this candidate. Try again."}


def screen_candidates(candidates: list[dict], role: str, jd: str, country: str = "US") -> dict:
    cands = [c for c in candidates if len((c.get("resume") or "").strip()) >= 30][:MAX_CANDIDATES]
    if not cands:
        raise ValueError("Add at least one candidate resume (30+ characters).")
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda c: _screen_one(c, role, jd, country), cands))
    ranked = sorted((r for r in results if r["ok"]), key=lambda r: -r["score"])
    failed = [r for r in results if not r["ok"]]
    return {"ranked": ranked, "failed": failed, "total": len(results)}
