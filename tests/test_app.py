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
from app import main as appmod

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
    assert c.post("/api/recruiter/screen", json=body).status_code == 403  # guests and candidates cannot use recruiter tools
    rc = TestClient(app)
    assert rc.post("/api/auth/register", json={"email": "rec1@example.com", "password": "longpassword1", "agree": True, "role": "recruiter"}).status_code == 200
    d = rc.post("/api/recruiter/screen", json=body).json()
    assert d["total"] == 2 and len(d["ranked"]) == 2
    assert d["ranked"][0]["score"] >= d["ranked"][1]["score"]
    assert rc.post("/api/recruiter/screen", json={"role": "QA", "candidates": []}).status_code == 400


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
    html = c.get("/").text + c.get("/static/app.js").text
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
    assert len(rs) == 33 and "Data Entry / MIS Executive" not in rs and "Customer Support (BPO)" not in rs
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
    assert "example.test" not in d["url"] and d["url"].startswith(appmod.PUBLIC_BASE.rstrip("/") + "/c/") and d["image"].endswith(".png") and d["verdict"]
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


def _new_sid():
    d = c.post("/api/session", json={"resume": RESUME, "role": "QA Engineer", "country": "US", "followups": False}).json()
    return d["session_id"]


def test_retry_rescores_without_advancing(monkeypatch):
    from app import llm

    sid = _new_sid()
    scores = iter([2, 4, 3, 5])

    def fake(task, system, user, model=None):
        if task == "turn":
            n = next(scores)
            return {"scores": {"clarity": n, "depth": n, "correctness": n, "star": n}, "feedback": "ok", "stronger_answer": "x",
                    "tips": [], "communication": {"fluency": 3}, "followup": ""}
        if task == "report":
            return {"overall_score": 4, "summary": "s", "strengths": [], "gaps": [], "plan_7_days": []}
        raise llm.LLMError("unused in this test")

    monkeypatch.setattr(llm, "chat_json", fake)
    r1 = c.post(f"/api/session/{sid}/answer", json={"answer": "I tested login flows."}).json()
    assert r1["feedback"]["scores"]["depth"] == 2
    r2 = c.post(f"/api/session/{sid}/retry", json={"answer": "I tested login flows with Selenium and cut failures."}).json()
    assert r2["new_avg"] > r2["previous_avg"] and r2["attempt"] == 2 and r2["retries_left"] == 2
    assert r2["first_scores"]["depth"] == 2
    # a worse retry never lowers the kept score; still on the same question
    r3 = c.post(f"/api/session/{sid}/retry", json={"answer": "Worse one."}).json()
    assert r3["new_avg"] < r3["previous_avg"]
    r4 = c.post(f"/api/session/{sid}/retry", json={"answer": "Best one now."}).json()
    assert r4["retries_left"] == 0
    assert c.post(f"/api/session/{sid}/retry", json={"answer": "one more"}).status_code == 400
    from app import services

    assert services.skill_scores(sid)["depth"] == 5.0
    assert c.post(f"/api/session/{sid}/retry", json={"answer": ""}).status_code == 400
    assert c.post("/api/session/nope/retry", json={"answer": "x"}).status_code == 404


def test_retry_needs_an_answer_first_and_not_after_followup(monkeypatch):
    sid = _new_sid()
    assert c.post(f"/api/session/{sid}/retry", json={"answer": "x"}).status_code == 400


def test_progress_recorded_for_logged_in_only():
    from fastapi.testclient import TestClient

    u = TestClient(app)
    assert u.get("/api/progress").status_code == 401
    assert u.post("/api/auth/register", json={"email": "prog@example.com", "password": "longenough1"}).status_code == 200
    sid = u.post("/api/session", json={"resume": RESUME, "role": "QA Engineer", "country": "US", "followups": False}).json()["session_id"]
    u.post(f"/api/session/{sid}/answer", json={"answer": "I built a Selenium suite."})
    assert u.get(f"/api/session/{sid}/report").status_code == 200
    u.get(f"/api/session/{sid}/report")  # second read must not duplicate
    pts = u.get("/api/progress").json()["points"]
    assert len(pts) == 1 and pts[0]["role"] == "QA Engineer" and "depth" in pts[0]["scores"]
    # a guest report records nothing and still works
    g = _new_sid()
    c.post(f"/api/session/{g}/answer", json={"answer": "I built a suite."})
    assert c.get(f"/api/session/{g}/report").status_code == 200
    # progress is deleted with the account
    assert u.delete("/api/auth/account").status_code == 200
    from app import accounts

    with accounts.Conn() as cn:
        assert cn.run("SELECT id FROM progress WHERE id=?", (sid,)) == []


def test_waitlist():
    assert c.post("/api/waitlist", json={"email": "Fan@Example.com"}).json() == {"ok": True, "new": True}
    assert c.post("/api/waitlist", json={"email": "fan@example.com"}).json() == {"ok": True, "new": False}
    assert c.post("/api/waitlist", json={"email": "nope"}).status_code == 400
    assert c.post("/api/waitlist", json={"email": "x" * 300 + "@a.com"}).status_code == 422


def _docx_bytes(paragraphs):
    import io
    import zipfile

    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_docx_upload_gives_clean_text_not_bytes():
    raw = _docx_bytes(["Ranjit Sahoo", "Fresher QA engineer, Bhubaneswar", "Skills: Python &amp; SQL"])
    r = c.post("/api/extract", files={"file": ("Resume (1).docx", raw, "application/octet-stream")})
    assert r.status_code == 200
    assert r.json()["text"] == "Ranjit Sahoo\nFresher QA engineer, Bhubaneswar\nSkills: Python & SQL"
    # detected by content even if the name is wrong
    assert c.post("/api/extract", files={"file": ("resume.txt", raw, "text/plain")}).json()["text"].startswith("Ranjit Sahoo")


def test_binary_and_broken_uploads_give_clear_errors():
    junk = bytes(range(256)) * 40
    for name in ("a.bin", "a.txt", "a.docx"):
        r = c.post("/api/extract", files={"file": (name, junk, "application/octet-stream")})
        assert r.status_code == 400 and "\ufffd" not in r.text
    assert c.post("/api/extract", files={"file": ("old.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x" * 50, "application/msword")}).status_code == 400
    assert c.post("/api/extract", files={"file": ("e.txt", b"  ", "text/plain")}).status_code == 400


def test_geo_from_cdn_header():
    assert c.get("/api/geo", headers={"cf-ipcountry": "IN"}).json()["country"] == "India"
    assert c.get("/api/geo", headers={"cf-ipcountry": "US"}).json()["country"] == "US"
    assert c.get("/api/geo", headers={"cf-ipcountry": "DE"}).json()["country"] == "Other"
    assert c.get("/api/geo").json()["country"] is None


def test_mock_interview_and_negotiation_work_without_a_resume():
    d = c.post("/api/session", json={"resume": "", "role": "Business Analyst", "country": "India"})
    assert d.status_code == 200 and d.json()["question"]["question"]
    assert c.post("/api/session", json={"resume": "", "role": "", "country": "India"}).status_code == 400
    n = c.post("/api/negotiation", json={"resume": "", "role": "Business Analyst", "country": "India"})
    assert n.status_code == 200


def _tiny_pdf(text):
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET"
    objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offs = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offs)
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF"
    return out.encode()


def test_pdf_upload_extracts_text():
    r = c.post("/api/extract", files={"file": ("cv.pdf", _tiny_pdf("Priya Sharma QA engineer in Pune with Selenium"), "application/pdf")})
    assert r.status_code == 200 and "Priya Sharma QA engineer in Pune" in r.json()["text"]
    assert c.post("/api/extract", files={"file": ("bad.pdf", b"%PDF-1.4 nonsense", "application/pdf")}).status_code == 400
