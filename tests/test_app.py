import os

os.environ.pop("NEBIUS_API_KEY", None)
os.environ["RATE_LIMIT_PER_MIN"] = "100000"
os.environ["AUTH_RATE_PER_MIN"] = "100000"
os.environ["SIGNUPS_PER_DAY"] = "100000"
os.environ["AI_DAILY_PER_IP"] = "100000"
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
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA Engineer", "followups": False}).json()
    sid, total = s["session_id"], s["total"]
    for i in range(total):
        r = c.post(f"/api/session/{sid}/answer", json={"answer": "I automated tests and cut time."}).json()
        assert set(r["feedback"]["scores"]) == {"clarity", "depth", "correctness", "star"}
        assert r["finished"] == (i == total - 1)
    rep = c.get(f"/api/session/{sid}/report").json()
    assert len(rep["plan_7_days"]) == 7
    assert c.post(f"/api/session/{sid}/answer", json={"answer": "x"}).status_code == 400


def test_report_needs_answers():
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA Engineer", "followups": False}).json()
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
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA", "country": "India", "followups": False}).json()
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
    s = c.post("/api/session", json={"resume": RESUME, "role": "QA", "followups": False}).json()
    codes = []
    ts = [threading.Thread(target=lambda: codes.append(c.post(f"/api/session/{s['session_id']}/answer", json={"answer": "a b c"}).status_code)) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert codes.count(200) == s["total"] and codes.count(400) == 6 - s["total"]


def test_ui_has_voice_controls():
    html = c.get("/").text
    for needle in ('id="vAccent"', 'en-IN', 'id="vRate"', "localStorage", "speechSynthesis"):
        assert needle in html


def test_pwa_assets():
    m = c.get("/static/manifest.webmanifest").json()
    assert m["display"] == "standalone" and len(m["icons"]) >= 2
    for i in m["icons"]:
        assert c.get(i["src"]).status_code == 200
    sw = c.get("/sw.js")
    assert sw.status_code == 200 and "javascript" in sw.headers["content-type"]
    assert 'rel="manifest"' in c.get("/").text


def test_bank_roles_and_curated():
    assert "QA Automation Engineer" in c.get("/api/bank/roles").json()["roles"]
    d = c.post("/api/bank", json={"role": "Selenium test engineer"}).json()
    assert d["matched"] and d["role"] == "QA Automation Engineer"
    assert len(d["questions"]) >= 10 and {"type", "level", "question", "hint"} <= set(d["questions"][0])
    assert d["company"] is None


def test_bank_unknown_role_falls_back_to_general():
    d = c.post("/api/bank", json={"role": "Astronaut"}).json()
    assert d["matched"] is False and d["role"] == "General" and d["questions"]


def test_bank_company_questions_cached_and_validated(monkeypatch):
    from app import bank

    bank._cache.clear()
    d = c.post("/api/bank", json={"role": "Java Developer", "company": "Acme Corp"}).json()
    assert d["company"]["company"] == "Acme Corp" and d["company"]["questions"]
    calls = []
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: calls.append(1) or {"questions": []})
    c.post("/api/bank", json={"role": "Java Developer", "company": "Acme Corp"})
    assert calls == []  # served from cache


def test_bank_company_failure_degrades(monkeypatch):
    from app import bank

    bank._cache.clear()

    def boom(*a, **k):
        raise llm.LLMError("x")

    monkeypatch.setattr(llm, "chat_json", boom)
    r = c.post("/api/bank", json={"role": "Python Developer", "company": "Zeta"})
    assert r.status_code == 200 and r.json()["company"] is None and r.json()["company_error"]


def test_bank_needs_input():
    assert c.post("/api/bank", json={}).status_code == 400


def test_coding_problems_listing_and_detail():
    ps = c.get("/api/coding/problems").json()["problems"]
    assert len(ps) >= 10 and {"id", "title", "level", "topic"} <= set(ps[0])
    d = c.get("/api/coding/problems/two-sum").json()
    assert d["statement"] and "Python" in d["starters"] and "SQL" not in d["languages"]
    assert c.get("/api/coding/problems/sql-second-highest").json()["languages"] == ["SQL"]
    assert c.get("/api/coding/problems/nope").status_code == 404


def test_coding_evaluate_ok_and_validation():
    code = "def solve(nums, t):\n    seen = {}\n    for i, n in enumerate(nums):\n        if t - n in seen: return [seen[t-n], i]\n        seen[n] = i\n"
    r = c.post("/api/coding/problems/two-sum/evaluate", json={"language": "Python", "code": code})
    assert r.status_code == 200
    d = r.json()
    assert d["verdict"] in ("correct", "partially_correct", "incorrect") and 1 <= d["score"] <= 10 and "time" in d["complexity"]
    assert c.post("/api/coding/problems/two-sum/evaluate", json={"language": "SQL", "code": code}).status_code == 400
    assert c.post("/api/coding/problems/two-sum/evaluate", json={"language": "Python", "code": "x"}).status_code == 400
    assert c.post("/api/coding/problems/two-sum/evaluate", json={"language": "Python", "code": "x" * 13000}).status_code == 400
    assert c.post("/api/coding/problems/zzz/evaluate", json={"language": "Python", "code": code}).status_code == 404


def test_coding_evaluate_sanitizes_model_output(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"verdict": "weird", "score": 99, "bugs": "nope", "complexity": "O(n)"})
    d = c.post("/api/coding/problems/two-sum/evaluate", json={"language": "Python", "code": "def solve(): pass"}).json()
    assert d["verdict"] == "partially_correct" and d["score"] == 10 and d["bugs"] == [] and d["complexity"]["optimal"] is False


def test_coding_hint_levels():
    d = c.post("/api/coding/problems/two-sum/hint", json={"level": 9}).json()
    assert d["level"] == 3 and d["hint"]


def test_builder_parse_polish_summary():
    d = c.post("/api/builder/parse", json={"resume": RESUME}).json()
    assert d["name"] and d["experience"][0]["bullets"] and isinstance(d["skills"], list)
    assert c.post("/api/builder/parse", json={"resume": "hi"}).status_code == 400
    b = c.post("/api/builder/polish", json={"role": "QA", "bullets": ["did testing", "wrote scripts"]}).json()["bullets"]
    assert len(b) == 2
    assert c.post("/api/builder/polish", json={"role": "QA", "bullets": ["", "  "]}).status_code == 400
    s = c.post("/api/builder/summary", json={"role": "QA", "facts": "5 years Selenium Java API testing at Acme"}).json()
    assert s["summary"]
    assert c.post("/api/builder/summary", json={"role": "QA", "facts": "x"}).status_code == 400


def test_builder_polish_misaligned_model_output_is_ignored(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"bullets": ["only one"]})
    b = c.post("/api/builder/polish", json={"role": "QA", "bullets": ["a b", "c d"]}).json()["bullets"]
    assert b == ["a b", "c d"]


def test_prep_pack_has_model_answers_and_coding():
    d = c.post("/api/prep", json={"resume": RESUME, "role": "QA Automation Engineer", "jd": "Selenium, Java, CI", "country": "US"}).json()
    assert d["questions"] and all(q["model_answer"] for q in d["questions"])
    assert d["coding_profile"] is True and len(d["questions"]) >= 2
    cq = c.post("/api/prep/coding", json={"resume": RESUME, "role": "QA Automation Engineer", "jd": "Selenium", "country": "US"}).json()
    assert cq["coding_questions"] and cq["coding_questions"][0]["solution"]
    assert c.post("/api/prep", json={"resume": "hi", "role": "QA"}).status_code == 400
    assert c.post("/api/prep", json={"resume": RESUME, "role": ""}).status_code == 400


def test_prep_skips_coding_call_for_non_technical(monkeypatch):
    from app import prep

    prep._cache.clear()
    seen = []
    real = llm.chat_json

    def spy(task, *a, **k):
        seen.append(task)
        return real(task, *a, **k)

    monkeypatch.setattr(llm, "chat_json", spy)
    hr = "Priya Rao. HR recruiter with 6 years in talent acquisition, onboarding and employee relations in Pune."
    d = c.post("/api/prep", json={"resume": hr, "role": "HR Manager", "country": "India"}).json()
    assert "prep_core" in seen and "prep_code" not in seen


def test_prep_cached(monkeypatch):
    from app import prep

    prep._cache.clear()
    body = {"resume": RESUME, "role": "QA Engineer", "country": "US"}
    c.post("/api/prep", json=body)
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should be cached")))
    assert c.post("/api/prep", json=body).status_code == 200


def test_company_profiles():
    ds = c.get("/api/companies").json()["companies"]
    assert "Google" in ds and "TCS" in ds and len(ds) >= 30
    d = c.post("/api/bank", json={"role": "Java Developer", "company": "tcs"}).json()
    assert d["profile"]["country"] == "India" and d["profile"]["rounds"]
    assert c.post("/api/bank", json={"role": "Java Developer", "company": "Unknown Startup"}).json()["profile"] is None
    assert c.post("/api/bank", json={"role": "QA", "company": "Cognizant", "country": "India"}).json()["profile"]["country"] == "India"


def test_known_company_is_instant_unless_ai_requested(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no AI call expected")))
    d = c.post("/api/bank", json={"role": "QA", "company": "Google"}).json()
    assert d["profile"]["name"] == "Google" and d["company"] is None


def test_us_market_roles_and_matching():
    from app import bank
    rs = bank.roles()
    for r in ["Salesforce Developer", "ServiceNow Developer", ".NET Developer", "AWS Cloud Engineer", "Cybersecurity Analyst", "Scrum Master"]:
        assert r in rs
    assert "US IT Recruiter" not in rs
    assert bank.match_role("senior dotnet core dev") == ".NET Developer"
    assert bank.match_role("cloud engineer") == "AWS Cloud Engineer"
    for r in rs:
        assert len(bank.curated(r)["questions"]) >= 15


def test_india_market_roles():
    from app import bank
    rs = bank.roles()
    assert len(rs) == 28 and "Data Entry / MIS Executive" not in rs and "Customer Support (BPO)" not in rs
    for r in ["Sales / Business Development Executive", "Accountant (Tally)", "Banking Operations", "UI/UX Designer"]:
        assert r in rs
        assert len([q for q in bank.curated(r)["questions"]]) >= 15
    assert bank.match_role("tally accountant") == "Accountant (Tally)"


def _start(**kw):
    return c.post("/api/session", json={"resume": RESUME, "role": "QA Engineer", **kw}).json()


def test_followup_flow_then_advance_and_depth_probe():
    d = _start()
    sid = d["session_id"]
    assert d["level"] == "auto"
    a = c.post(f"/api/session/{sid}/answer", json={"answer": "I automated tests in Selenium for a payments app."}).json()
    assert a["followup"]["type"] == "follow-up" and a["followup"]["n"] == 1 and a["number"] == 1 and not a["finished"]
    b = c.post(f"/api/session/{sid}/answer", json={"answer": "The hardest part was flaky waits, so I used explicit waits."}).json()
    assert "followup" not in b and b["number"] == 2 and b["next_question"]


def test_followups_can_be_turned_off_and_level_is_kept():
    d = _start(followups=False, level="brutal")
    assert d["level"] == "brutal"
    a = c.post(f"/api/session/{d['session_id']}/answer", json={"answer": "I wrote Selenium tests."}).json()
    assert "followup" not in a and a["number"] == 2
    assert _start(level="nonsense")["level"] == "auto"


def test_difficulty_adjusts_after_strong_answer(monkeypatch):
    from app import mock
    orig = mock.reply

    def strong(task, user):
        r = orig(task, user)
        if task == "turn":
            r = dict(r, scores={"clarity": 5, "depth": 5, "correctness": 5, "star": 5})
        return r

    monkeypatch.setattr(mock, "reply", strong)
    sid = _start(followups=False)["session_id"]
    a = c.post(f"/api/session/{sid}/answer", json={"answer": "Excellent detailed answer with numbers."}).json()
    assert a["difficulty"] == "harder" and a["next_question"]["question"].startswith("Adjusted question")


def test_report_includes_followup_turns_and_score_card():
    sid = _start()["session_id"]
    c.post(f"/api/session/{sid}/answer", json={"answer": "I automated tests in Selenium."})
    c.post(f"/api/session/{sid}/answer", json={"answer": "Explicit waits fixed the flaky tests."})
    r = c.post(f"/api/session/{sid}/card", json={"name": "Jane <b>Doe</b>"}, headers={"host": "example.test"})
    assert r.status_code == 200
    d = r.json()
    assert d["url"].startswith("http://example.test/c/") and d["image"].endswith(".png") and d["verdict"]
    tok = d["url"].rsplit("/c/", 1)[1]
    img = c.get(f"/c/{tok}.png")
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    page = c.get(f"/c/{tok}").text
    assert "og:image" in page and "<b>Doe" not in page and "Jane" in page
    assert c.get(f"/c/{tok[:-3]}abc.png").status_code == 404
    assert c.get("/c/garbage").status_code == 404


def test_card_requires_an_answer_first():
    sid = _start()["session_id"]
    assert c.post(f"/api/session/{sid}/card", json={}).status_code == 400


def test_star_builder_and_validation():
    r = c.post("/api/star", json={"experience": "Two teammates fought about test ownership before release and I sorted it out.", "question": "Tell me about a conflict", "role": "QA", "country": "India"})
    assert r.status_code == 200
    d = r.json()
    assert d["spoken_answer"] and d["situation"] and d["result"] and isinstance(d["missing"], list)
    assert c.post("/api/star", json={"experience": "short"}).status_code == 400


def test_company_brief_and_validation():
    r = c.post("/api/company-brief", json={"company": "Infosys", "role": "Java Developer", "country": "India"})
    assert r.status_code == 200
    d = r.json()
    assert d["summary"] and d["process"] and d["news_url"].startswith("https://news.google.com/search?q=Infosys")
    assert d["known_profile"] is True
    assert c.post("/api/company-brief", json={"company": " "}).status_code == 400


def test_security_headers_and_no_docs():
    r = c.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 404


def test_spoofed_forwarded_for_not_trusted():
    from app.guard import client_key

    class R:
        def __init__(s, h):
            s.headers, s.client = h, None

    assert client_key(R({"cf-connecting-ip": "9.9.9.9", "x-forwarded-for": "1.1.1.1, 9.9.9.9, 2.2.2.2, 10.0.0.1"})) == "9.9.9.9"
    assert client_key(R({"x-forwarded-for": "1.1.1.1, 9.9.9.9, 2.2.2.2, 10.0.0.1"})) == "9.9.9.9"


def test_daily_model_budget(monkeypatch):
    from app import llm

    monkeypatch.setattr(llm, "DAILY_CAP", 0)
    import pytest

    with pytest.raises(llm.LLMError):
        llm._budget()


def test_fail_limiter():
    from app.guard import FailLimiter

    f = FailLimiter(3, 600)
    for _ in range(3):
        assert not f.blocked("a")
        f.fail("a")
    assert f.blocked("a") and not f.blocked("b")


def test_bad_host_header_falls_back():
    r = c.post("/api/session/none/card", json={"name": "x"}, headers={"host": "evil.com\"><script>"})
    assert r.status_code in (404, 400, 422)


def test_idor_history_and_unhandled_error():
    a = TestClient(app)
    b = TestClient(app)
    a.post("/api/auth/register", json={"email": "ida@example.com", "password": "password123"})
    rb = b.post("/api/auth/register", json={"email": "idb@example.com", "password": "password123"}); assert rb.status_code == 200, rb.text
    iid = a.post("/api/history", json={"kind": "star", "title": "t", "data": {"x": 1}}).json()["id"]
    assert a.get(f"/api/history/{iid}").status_code == 200
    assert b.get(f"/api/history/{iid}").status_code == 404
    assert b.delete(f"/api/history/{iid}").status_code == 404
    assert a.get(f"/api/history/{iid}").status_code == 200
    assert TestClient(app).get(f"/api/history/{iid}").status_code == 401


def test_spend_guard_blocks_when_budget_used(monkeypatch):
    import pytest

    from app import llm, spend

    spend._cache.update(t=0.0)
    s0 = spend.status()["total_usd"]
    spend.record(1.25)
    assert spend.status()["total_usd"] >= s0 + 1.25
    monkeypatch.setattr(spend, "TOTAL_CAP", s0 + 1.0)
    spend._cache.update(t=0.0)
    with pytest.raises(spend.BudgetExceeded):
        spend.check()
    assert spend.cost(True, 1000, 1000) > 0


def test_budget_exhausted_returns_503(monkeypatch):
    from app import llm

    def boom(*a, **k):
        raise llm.LLMError("budget")

    monkeypatch.setattr("app.prep.build", boom)
    r = c.post("/api/prep", json={"resume": "x" * 60, "role": "QA Engineer", "country": "US"})
    assert r.status_code == 503 and "capacity" in r.json()["detail"]


def test_grounding_helpers():
    from app.services import invented_details, ungrounded_names

    src = ("Built a framework with BasePage and TestNG, 450 tests, cut regression from 2 days to 3 hours", "run the suites")
    assert ungrounded_names("How does your ConfigReader pick a file?", *src) == ["ConfigReader"]
    assert ungrounded_names("How did you design BasePage?", *src) == []
    assert invented_details("I used 16 threads on 4 Grid nodes", *src)
    assert invented_details("I wrote a DataProvider with Jackson", *src)
    assert not invented_details("I cut regression from 2 days to 3 hours across 450 tests with BasePage", *src)
    assert "[add your number]" in "x [add your number]"


def test_followup_naming_unsaid_thing_is_dropped(monkeypatch):
    from app import llm, services

    def fake(task, system, user, model=None):
        if task == "turn":
            return {"scores": {"clarity": 3, "depth": 3, "correctness": 3, "star": 3}, "feedback": "ok", "stronger_answer": "x", "tips": [],
                    "communication": {}, "followup": "How does your ConfigReader load files?"}
        from app import mock

        return mock.reply(task, user)

    monkeypatch.setattr(llm, "chat_json", fake)
    d = c.post("/api/session", json={"resume": "QA engineer with Selenium and TestNG experience " * 3, "role": "QA", "country": "US", "followups": True}).json()
    r = c.post(f"/api/session/{d['session_id']}/answer", json={"answer": "I built a Selenium suite with TestNG."}).json()
    assert "followup" not in r or not r["followup"]
