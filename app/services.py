import re
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
LEVELS = {
    "auto": "Calibrate to the seniority shown on the resume and role.",
    "fresher": "Entry level (0-2 years): fundamentals, simple practical scenarios, supportive but realistic.",
    "experienced": "Mid to senior: depth, design trade-offs, ownership, and real production situations.",
    "brutal": "Very demanding, top-company bar: hard problems, edge cases, probing every assumption, senior-level expectations.",
}
MAX_FOLLOWUPS = 2


def _level(v) -> str:
    v = (v or "auto").strip().lower()
    return v if v in LEVELS else "auto"


def start_session(resume: str, role: str, jd: str = "", country: str = "US", level: str = "auto", followups: bool = True, count: int = N_QUESTIONS) -> dict:
    country = market.normalize(country)
    level = _level(level)
    count = max(3, min(int(count), 8))
    qs = llm.chat_json(
        "questions",
        _sys(prompts.QUESTIONS_SYSTEM, country, n=count, level_note=LEVELS[level]),
        _ctx(resume, role, jd),
        model=llm.FAST_MODEL,
    ).get("questions", [])[:count]
    if not qs:
        raise llm.LLMError("no questions generated")
    data = {
        "kind": "interview", "country": country, "resume": resume[:MAX_RESUME_CHARS], "role": role, "jd": jd[:MAX_JD_CHARS],
        "questions": qs, "index": 0, "turns": [], "done": False, "level": level, "followups": bool(followups),
        "pending": None, "group": [],
    }
    sid = db.create(data)
    return {"session_id": sid, "question": qs[0], "number": 1, "total": len(qs), "country": country, "level": level}


def _interview(sid: str) -> dict:
    s = db.load(sid)
    if s is None or s.get("kind") != "interview":
        raise KeyError(sid)
    return s


def _perf(fb: dict) -> float:
    sc = fb.get("scores") or {}
    vals = []
    for k in ("clarity", "depth", "correctness"):
        try:
            vals.append(float(sc.get(k)))
        except (TypeError, ValueError):
            pass
    return sum(vals) / len(vals) if vals else 3.0


def _adjust_next(s: dict) -> str | None:
    """Make the next main question harder or easier based on how this question went. Never blocks the flow."""
    g = s.get("group") or []
    nxt = s["index"]
    if not g or nxt >= len(s["questions"]):
        return None
    avg = sum(g) / len(g)
    if avg >= 4.2:
        direction, note, tag = "noticeably harder and more probing", "very well", "harder"
    elif avg <= 2.2 and s.get("level") != "brutal":
        direction, note, tag = "a little easier and more approachable", "with difficulty", "easier"
    else:
        return None
    try:
        q = s["questions"][nxt]
        out = llm.chat_json(
            "adjust_q",
            _sys(prompts.ADJUST_SYSTEM, s["country"], direction=direction, direction_note=note),
            f"{_ctx(s['resume'], s['role'], s['jd'])}\n\nNEXT QUESTION ({q['type']}): {q['question']}",
            model=llm.FAST_MODEL,
        )
        if isinstance(out, dict) and str(out.get("question", "")).strip():
            qt = out.get("type") if out.get("type") in ("technical", "behavioral", "scenario") else q["type"]
            s["questions"][nxt] = {"type": qt, "question": str(out["question"]).strip()[:600]}
            return tag
    except llm.LLMError:
        pass
    return None


def load_interview(sid: str) -> dict:
    return _interview(sid)


_CAMEL = re.compile(r"\b[A-Za-z]*[a-z][A-Z][A-Za-z]*\b")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ungrounded_names(text: str, *sources: str) -> list[str]:
    """CamelCase identifiers (class, tool or library names) in `text` that appear nowhere in the sources."""
    hay = _norm(" ".join(sources))
    return [t for t in dict.fromkeys(_CAMEL.findall(text or "")) if _norm(t) not in hay]


def invented_details(text: str, *sources: str) -> bool:
    """True when a model-written answer contains numbers or CamelCase names the candidate never gave."""
    hay = " ".join(sources)
    nums = set(_NUM.findall(hay))
    return bool(ungrounded_names(text, hay)) or any(n not in nums for n in _NUM.findall(text or ""))


def answer(sid: str, text: str) -> dict:
    with _lock(sid):
        s = _interview(sid)
        if s["done"]:
            raise ValueError("session already finished")
        main_q = s["questions"][s["index"]]
        pend = s.get("pending")
        if pend:
            q = {"type": "follow-up", "question": pend["question"]}
            user = (
                f"{_ctx(s['resume'], s['role'], s['jd'])}\n\nMAIN QUESTION: {main_q['question']}\n"
                f"INTERVIEWER FOLLOW-UP: {q['question']}\n\nCANDIDATE ANSWER TO THE FOLLOW-UP:\n{text[:4000]}"
            )
            model = llm.FAST_MODEL  # follow-ups stay quick
        else:
            q = main_q
            user = f"{_ctx(s['resume'], s['role'], s['jd'])}\n\nQUESTION ({q['type']}): {q['question']}\n\nCANDIDATE ANSWER:\n{text[:4000]}"
            model = llm.STRONG_MODEL
        fb = llm.chat_json("turn", _sys(prompts.TURN_SYSTEM, s["country"]), user, model=model)
        if not isinstance(fb, dict):
            raise llm.LLMError("bad feedback")
        fb.setdefault("communication", {})
        fb["communication"]["metrics"] = comms.analyze(text)
        src = (s["resume"], s["jd"], main_q["question"], text)
        if invented_details(str(fb.get("stronger_answer") or ""), *src):
            fb["stronger_answer_note"] = "This sample includes example details (numbers or names) you did not give. Replace them with your real ones, or leave them out."
        s["turns"].append({"question": q, "answer": text, "feedback": fb, "followup": bool(pend)})
        s.setdefault("group", []).append(_perf(fb))
        done_n = pend["n"] if pend else 0
        fu = " ".join(str(fb.get("followup") or "").split())[:400]
        if fu and ungrounded_names(fu, s["resume"], s["jd"], main_q["question"], text, *(t["answer"] for t in s["turns"])):
            fu = ""  # the follow-up names something the candidate never said: skip it rather than mislead
        try:
            depth = float((fb.get("scores") or {}).get("depth", 3))
        except (TypeError, ValueError):
            depth = 3.0
        if s.get("followups", True) and fu and (done_n == 0 or (done_n < MAX_FOLLOWUPS and depth <= 2)):
            s["pending"] = {"question": fu, "n": done_n + 1}
            db.save(sid, s)
            return {
                "feedback": fb, "finished": False, "followup": {"type": "follow-up", "question": fu, "n": done_n + 1, "max": MAX_FOLLOWUPS},
                "number": s["index"] + 1, "total": len(s["questions"]),
            }
        s["pending"] = None
        s["index"] += 1
        finished = s["index"] >= len(s["questions"])
        s["done"] = finished
        shift = None if finished else _adjust_next(s)
        s["group"] = []
        db.save(sid, s)
    out = {"feedback": fb, "finished": finished}
    if not finished:
        out["next_question"] = s["questions"][s["index"]]
        out["number"] = s["index"] + 1
        out["total"] = len(s["questions"])
        if shift:
            out["difficulty"] = shift
    return out


MAX_RETRIES = 3
_SKILLS = ("clarity", "depth", "correctness", "star")


def retry(sid: str, text: str) -> dict:
    """Re-score a better attempt at the last main question. Does not move the interview forward."""
    with _lock(sid):
        s = _interview(sid)
        if "report" in s:
            raise ValueError("The report is already made. Start a new session to practise more.")
        if not s["turns"]:
            raise ValueError("Answer a question first.")
        t = s["turns"][-1]
        if t.get("followup"):
            raise ValueError("You can retry the main question answer, not a follow-up.")
        tries = t.setdefault("retries", [])
        if len(tries) >= MAX_RETRIES:
            raise ValueError("That is 3 retries on this question. Move on to the next one.")
        q = t["question"]
        user = f"{_ctx(s['resume'], s['role'], s['jd'])}\n\nQUESTION ({q['type']}): {q['question']}\n\nCANDIDATE ANSWER:\n{text[:4000]}"
        fb = llm.chat_json("turn", _sys(prompts.TURN_SYSTEM, s["country"]), user, model=llm.STRONG_MODEL)
        if not isinstance(fb, dict):
            raise llm.LLMError("bad feedback")
        fb.setdefault("communication", {})
        fb["communication"]["metrics"] = comms.analyze(text)
        if invented_details(str(fb.get("stronger_answer") or ""), s["resume"], s["jd"], q["question"], text):
            fb["stronger_answer_note"] = "This sample includes example details (numbers or names) you did not give. Replace them with your real ones, or leave them out."
        fb.pop("followup", None)
        before = _perf(t.get("best") or t["feedback"])
        tries.append({"answer": text, "feedback": fb})
        now = _perf(fb)
        if now >= before:
            t["best"] = fb
            t["best_answer"] = text
        db.save(sid, s)
    return {
        "feedback": fb, "attempt": len(tries) + 1, "retries_left": MAX_RETRIES - len(tries),
        "first_scores": t["feedback"].get("scores"), "previous_avg": round(before, 2), "new_avg": round(now, 2),
    }


def skill_scores(sid: str) -> dict:
    """Average 1-5 score per skill across the answered main questions (best attempt counts)."""
    s = _interview(sid)
    acc = {k: [] for k in (*_SKILLS, "fluency")}
    for t in s["turns"]:
        fb = t.get("best") or t["feedback"]
        for k in _SKILLS:
            try:
                acc[k].append(float((fb.get("scores") or {})[k]))
            except (KeyError, TypeError, ValueError):
                pass
        try:
            acc["fluency"].append(float((fb.get("communication") or {})["fluency"]))
        except (KeyError, TypeError, ValueError):
            pass
    return {k: round(sum(v) / len(v), 2) for k, v in acc.items() if v}


def report(sid: str) -> dict:
    with _lock(sid):
        s = _interview(sid)
        if "report" in s:
            return s["report"]
        if not s["turns"]:
            raise ValueError("answer at least one question first")
        transcript = "\n\n".join(
            f"Q ({t['question']['type']}): {t['question']['question']}\nA: {t.get('best_answer') or t['answer']}\n"
            f"Scores: {(t.get('best') or t['feedback']).get('scores')}\nFeedback: {(t.get('best') or t['feedback']).get('feedback')}\n"
            f"Speech metrics: {(t.get('best') or t['feedback'])['communication'].get('metrics')}"
            + (f"\n(Candidate retried this answer {len(t['retries'])} time(s) and improved it.)" if t.get("best") else "")
            for t in s["turns"]
        )
        rep = llm.chat_json(
            "report", _sys(prompts.REPORT_SYSTEM, s["country"]), f"ROLE: {s['role']} (difficulty: {s.get('level', 'auto')})\n\n{transcript}", model=llm.STRONG_MODEL
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
        r["recommendation"] = "advance" if r["score"] >= 70 else "maybe" if r["score"] >= 50 else "reject"
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
