import os

os.environ.pop("NEBIUS_API_KEY", None)
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
