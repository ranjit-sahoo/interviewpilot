import os

os.environ.pop("NEBIUS_API_KEY", None)
os.environ["RATE_LIMIT_PER_MIN"] = "100000"
os.environ["INTERVIEWPILOT_DB"] = ":memory:"

import tempfile

os.environ["INTERVIEWPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "t.sqlite3")

from fastapi.testclient import TestClient

from app.main import app
from app import llm

c = TestClient(app)
RESUME = "Jane Doe. QA engineer with 5 years of experience in Selenium, Java and API testing at Acme Corp."


def test_health():
    r = c.get("/health").json()
    assert r["status"] == "ok" and r["mock_mode"] is True


def test_resume_review():
    r = c.post("/api/resume/review", data={"role": "QA Engineer", "resume": RESUME})
    assert r.status_code == 200
    d = r.json()
    assert d["weaknesses"] and "fix" in d["weaknesses"][0]


def test_resume_review_too_short():
    assert c.post("/api/resume/review", data={"role": "QA", "resume": "hi"}).status_code == 400


def test_full_interview_flow():
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA Engineer"}).json()
    sid, total = s["session_id"], s["total"]
    for i in range(total):
        r = c.post(f"/api/session/{sid}/answer", json={"answer": "I automated tests and cut time."}).json()
        assert set(r["feedback"]["scores"]) == {"clarity", "depth", "correctness", "star"}
        assert r["finished"] == (i == total - 1)
    rep = c.get(f"/api/session/{sid}/report").json()
    assert len(rep["plan_7_days"]) == 7
    assert c.post(f"/api/session/{sid}/answer", json={"answer": "x"}).status_code == 400


def test_report_needs_answers():
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA Engineer"}).json()
    assert c.get(f"/api/session/{s['session_id']}/report").status_code == 400


def test_extract_json_handles_fences_and_think():
    assert llm.extract_json('<think>hmm</think>```json\n{"a": 1}\n```') == {"a": 1}


# ---------- new features ----------
import threading

from app import comms, market
from app.guard import RateLimiter

JD = "We need a QA Automation Engineer with Selenium, Java, CI/CD, Docker and Postman experience for a US client."


def test_country_heuristic():
    assert market.detect_heuristic("Ravi, Hyderabad +91 98765 43210, B.Tech, TCS")["country"] == "India"
    assert market.detect_heuristic("John, Dallas TX, H1B, W2, 5 years")["country"] == "US"
    assert market.detect_heuristic("hello world")["country"] == "Other"
    assert market.normalize("usa") == "US" and market.normalize("weird") == "Other"


def test_detect_endpoint():
    r = c.post("/api/detect-country", json={"resume": "Ravi Kumar, Bengaluru +91 99999 99999. B.Tech. Infosys", "jd": ""})
    assert r.status_code == 200 and r.json()["country"] == "India"
    assert c.post("/api/detect-country", json={"resume": "x"}).status_code == 400


def test_match_endpoint():
    d = c.post("/api/match", json={"resume": RESUME, "role": "QA", "jd": JD}).json()
    assert 0 <= d["match_score"] <= 100 and d["missing_keywords"] and d["gaps"]
    assert c.post("/api/match", json={"resume": RESUME, "role": "QA", "jd": "short"}).status_code == 400


def test_comms_metrics():
    m = comms.analyze("Um, basically I like, you know, built the API. So I basically tested it.")
    assert m["fillers"].get("um") == 1 and m["fillers"].get("basically") == 2 and m["filler_total"] >= 4
    assert comms.analyze("")["word_count"] == 0 and comms.analyze("short answer")["too_short"]


def test_interview_has_country_and_communication():
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA", "country": "India"}).json()
    assert s["country"] == "India"
    r = c.post(f"/api/session/{s['session_id']}/answer", json={"answer": "Um I basically automated tests."}).json()
    comm = r["feedback"]["communication"]
    assert comm["fluency"] and comm["metrics"]["fillers"]["um"] == 1


def test_negotiation_flow():
    s = c.post("/api/negotiation", json={"resume": RESUME, "role": "QA Engineer", "country": "US"}).json()
    sid = s["session_id"]
    assert s["scenario"]["offer"]
    r = c.post(f"/api/negotiation/{sid}/say", json={"message": "I was hoping for 110k given my results."}).json()
    assert r["recruiter_reply"] and r["coach"]["better_line"] and r["finished"] is False
    rep = c.get(f"/api/negotiation/{sid}/report").json()
    assert rep["script"]
    assert c.post(f"/api/negotiation/{sid}/say", json={"message": "more"}).status_code == 400
    # a negotiation id is not an interview id and vice versa
    assert c.get(f"/api/session/{sid}/report").status_code == 404


def test_negotiation_report_needs_message():
    s = c.post("/api/negotiation", json={"resume": RESUME, "role": "QA"}).json()
    assert c.get(f"/api/negotiation/{s['session_id']}/report").status_code == 400


def test_recruiter_screening_ranks():
    body = {"role": "QA", "jd": JD, "candidates": [{"name": "A", "resume": RESUME}, {"name": "B", "resume": RESUME + " more text here"}, {"name": "C", "resume": "tiny"}]}
    d = c.post("/api/recruiter/screen", json=body).json()
    assert d["total"] == 2 and len(d["ranked"]) == 2
    assert d["ranked"][0]["score"] >= d["ranked"][1]["score"]
    assert c.post("/api/recruiter/screen", json={"role": "QA", "candidates": []}).status_code == 400


def test_extract_txt_upload():
    r = c.post("/api/extract", files={"file": ("r.txt", RESUME.encode(), "text/plain")})
    assert r.json()["text"].startswith("Jane")
    assert c.post("/api/extract", files={"file": ("r.txt", b"hi", "text/plain")}).status_code == 400


def test_rate_limiter_window():
    rl = RateLimiter(limit=3, window=10)
    assert all(rl.check("a", now=t) for t in (0, 1, 2))
    assert not rl.check("a", now=3)
    assert rl.check("b", now=3)
    assert rl.check("a", now=11)


def test_llm_failure_returns_502(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("x")

    monkeypatch.setattr(llm, "chat_json", boom)
    r = c.post("/api/match", json={"resume": RESUME, "role": "QA", "jd": JD})
    assert r.status_code == 502 and "try again" in r.json()["detail"]


def test_concurrent_users_do_not_collide():
    sids, errors = [], []

    def run():
        try:
            s = c.post("/api/session", json={"resume": RESUME, "role": "QA"}).json()
            for _ in range(s["total"]):
                assert c.post(f"/api/session/{s['session_id']}/answer", json={"answer": "answer text"}).status_code == 200
            sids.append(s["session_id"])
        except Exception as e:  # noqa
            errors.append(e)

    ts = [threading.Thread(target=run) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors and len(set(sids)) == 8


def test_same_session_parallel_answers_are_serialized():
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA"}).json()
    codes = []
    ts = [threading.Thread(target=lambda: codes.append(c.post(f"/api/session/{s['session_id']}/answer", json={"answer": "a b c"}).status_code)) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert codes.count(200) == s["total"] and codes.count(400) == 6 - s["total"]


def test_ui_has_voice_controls():
    html = c.get("/").text
    for needle in ('id="vAccent"', 'en-IN', 'id="vRate"', "localStorage", "speechSynthesis"):
        assert needle in html
