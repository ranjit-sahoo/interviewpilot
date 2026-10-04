from app import db, llm, prompts

MAX_RESUME_CHARS = 12000
N_QUESTIONS = 5


def _ctx(resume: str, role: str, jd: str = "") -> str:
    s = f"TARGET ROLE: {role}\n\nRESUME:\n{resume[:MAX_RESUME_CHARS]}"
    if jd.strip():
        s += f"\n\nJOB DESCRIPTION:\n{jd[:6000]}"
    return s


def review_resume(resume: str, role: str, jd: str = ""):
    """Resume weaknesses + how to fix them (strong model)."""
    return llm.chat_json("resume_review", prompts.RESUME_SYSTEM, _ctx(resume, role, jd), model=llm.STRONG_MODEL)


def start_session(resume: str, role: str, jd: str = "") -> dict:
    qs = llm.chat_json(
        "questions", prompts.QUESTIONS_SYSTEM.format(n=N_QUESTIONS), _ctx(resume, role, jd), model=llm.FAST_MODEL
    )["questions"][:N_QUESTIONS]
    data = {"resume": resume[:MAX_RESUME_CHARS], "role": role, "jd": jd, "questions": qs, "index": 0, "turns": [], "done": False}
    sid = db.create(data)
    return {"session_id": sid, "question": qs[0], "number": 1, "total": len(qs)}


def answer(sid: str, text: str) -> dict:
    s = db.load(sid)
    if s is None:
        raise KeyError(sid)
    if s["done"]:
        raise ValueError("session already finished")
    q = s["questions"][s["index"]]
    user = f"{_ctx(s['resume'], s['role'], s['jd'])}\n\nQUESTION ({q['type']}): {q['question']}\n\nCANDIDATE ANSWER:\n{text}"
    # Scoring uses the strong model; the interviewer follow-up comes from the same JSON.
    fb = llm.chat_json("turn", prompts.TURN_SYSTEM, user, model=llm.STRONG_MODEL)
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
    s = db.load(sid)
    if s is None:
        raise KeyError(sid)
    if "report" in s:
        return s["report"]
    if not s["turns"]:
        raise ValueError("answer at least one question first")
    transcript = "\n\n".join(
        f"Q ({t['question']['type']}): {t['question']['question']}\nA: {t['answer']}\n"
        f"Scores: {t['feedback'].get('scores')}\nFeedback: {t['feedback'].get('feedback')}"
        for t in s["turns"]
    )
    rep = llm.chat_json("report", prompts.REPORT_SYSTEM, f"ROLE: {s['role']}\n\n{transcript}", model=llm.STRONG_MODEL)
    s["report"] = rep
    db.save(sid, s)
    return rep
