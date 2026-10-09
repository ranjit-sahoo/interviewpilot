import os
import tempfile

os.environ.pop("NEBIUS_API_KEY", None)
os.environ.pop("DATABASE_URL", None)
for k in ("RATE_LIMIT_PER_MIN", "AUTH_RATE_PER_MIN", "SIGNUPS_PER_DAY", "AI_DAILY_PER_IP"):
    os.environ[k] = "100000"
os.environ["INTERVIEWPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "hub.sqlite3")

from fastapi.testclient import TestClient

from app import accounts, hubdata, hubparse, screening
from app.main import app

accounts.SQLITE_PATH = os.environ["INTERVIEWPILOT_DB"]


def client():
    return TestClient(app)


def reg(c, email, role, invite=""):
    r = c.post("/api/auth/register", json={"email": email, "password": "longpassword1", "agree": True, "role": role, "invite": invite})
    assert r.status_code == 200, r.text
    return r.json()


def test_roles_are_separate():
    rc, cc = client(), client()
    reg(rc, "r1@example.com", "recruiter")
    reg(cc, "c1@example.com", "candidate")
    assert rc.get("/api/auth/me").json()["user"]["role"] == "recruiter"
    assert cc.get("/api/auth/me").json()["user"]["role"] == "candidate"
    assert cc.get("/api/hub/campaigns").status_code == 403
    assert client().get("/api/hub/campaigns").status_code == 403
    assert rc.post("/api/prep", json={"role": "QA", "resume": "x" * 200}).status_code == 403  # recruiters cannot use candidate tools
    assert rc.post("/api/hub/campaigns", json={"name": "T"}).status_code == 200
    # login must match the declared role
    r = client().post("/api/auth/login", json={"email": "c1@example.com", "password": "longpassword1", "role": "recruiter"})
    assert r.status_code == 401
    r = client().post("/api/auth/login", json={"email": "c1@example.com", "password": "longpassword1", "role": "candidate"})
    assert r.status_code == 200
    assert client().post("/api/auth/register", json={"email": "c2@example.com", "password": "longpassword1", "agree": True, "role": "candidate", "invite": "R123"}).status_code == 400


def test_parse_rank_duplicates():
    t = "Priya Nair\npriya@example.com +91 98765 43210\nBengaluru\n5 years in customer service, voice process, excel. B.Com graduate. Notice period: 30 days"
    p = hubparse.parse(t)
    assert p["email"] == "priya@example.com" and p["phone"].endswith("9876543210") and p["years"] == 5 and p["city"] == "Bengaluru"
    assert {"excel", "customer-service"} <= set(p["skills"])
    rows = hubparse.rank([{"text": t}, {"text": t}, {"text": "Ravi 2 years sales Mumbai"}], must=["excel"], min_years=3)
    assert rows[0]["score"] >= rows[-1]["score"] and any(r["duplicate_of"] is not None for r in rows)


def test_scoring_helpers():
    assert screening.typing_result("a b c d", "a b c d", 60)["accuracy"] == 100
    assert screening.reading_result("hello there world", "hello world")["match"] > 50
    assert screening.mcq_result([{"a": 1}, {"a": 0}], [1, 1])["correct"] == 1
    a = hubdata.aptitude(7)
    assert a == hubdata.aptitude(7) and all(0 <= i["a"] < len(i["o"]) for i in a)
    q = screening.draw_questions("bpo", 6, "t")
    assert q[0]["q"].startswith("Tell me") and len({x["q"] for x in q}) == len(q)
    assert screening.draw_questions("bpo", 6, "t") == q and screening.draw_questions("bpo", 6, "u") != q
    assert "example" in screening.follow_up("Q", "short", "s") or "more" in screening.follow_up("Q", "short", "s")


def test_screening_flow_one_attempt_and_deletion():
    rc = client()
    reg(rc, "r2@example.com", "recruiter")
    cid = rc.post("/api/hub/campaigns", json={"name": "BPO drive", "pool": "bpo", "modules": ["voice", "typing", "quiz", "aptitude", "reading"], "n_questions": 3, "retention_days": 7}).json()["id"]
    inv = rc.post(f"/api/hub/campaigns/{cid}/invite", json={"candidates": [{"name": "Asha", "phone": "98765 43210"}]}).json()["invites"][0]
    assert inv["phone"] == "919876543210"
    tok = inv["token"]
    pub = client()
    assert pub.get(f"/api/s/{tok}").json()["status"] == "invited"
    assert pub.post(f"/api/s/{tok}/start", json={"consent": False}).status_code == 400
    st = pub.post(f"/api/s/{tok}/start", json={"consent": True}).json()
    plan = st["plan"]
    assert "a" not in plan["quiz"][0] and len(plan["voice"]) == 3 and "ref" not in plan["voice"][0]
    for i in range(3):
        r = pub.post(f"/api/s/{tok}/voice", json={"idx": i, "text": "My name is Asha. I completed graduation in commerce because I like to help people. For example I helped my neighbour.", "think": 2, "secs": 20, "pauses": 2})
        assert r.status_code == 200 and r.json()["follow_up"]
        assert pub.post(f"/api/s/{tok}/voice", json={"idx": i, "text": "I helped my neighbour with her bank form and she thanked me.", "followup": True}).status_code == 200
    assert pub.post(f"/api/s/{tok}/voice", json={"idx": 0, "text": "again"}).status_code == 409
    assert pub.post(f"/api/s/{tok}/module", json={"module": "typing", "typed": plan["typing"], "secs": 60}).status_code == 200
    assert pub.post(f"/api/s/{tok}/module", json={"module": "quiz", "answers": [0] * 10}).status_code == 200
    assert pub.post(f"/api/s/{tok}/module", json={"module": "aptitude", "answers": [0] * 12}).status_code == 200
    assert pub.post(f"/api/s/{tok}/module", json={"module": "reading", "said": plan["reading"]}).status_code == 200
    assert pub.post(f"/api/s/{tok}/finish", json={"leaves": 4}).status_code == 200
    assert pub.post(f"/api/s/{tok}/start", json={"consent": True}).status_code == 409  # one attempt only
    res = rc.get(f"/api/hub/campaigns/{cid}").json()
    a = res["attempts"][0]
    assert a["status"] == "done" and a["score"] is not None and any("Left the page" in s for s in a["signals"]) and len(a["voice"]) == 3
    assert rc.get("/api/hub/dashboard").json()["completed"] == 1
    assert pub.delete(f"/api/s/{tok}/mine").status_code == 200
    assert pub.get(f"/api/s/{tok}").status_code == 404


def test_open_link_one_per_phone_and_closed_campaign():
    rc = client()
    reg(rc, "r3@example.com", "recruiter")
    cid = rc.post("/api/hub/campaigns", json={"name": "Open", "modules": ["quiz"]}).json()["id"]
    pub = client()
    r = pub.post(f"/api/s/o-{cid}/start", json={"name": "Ravi", "phone": "9123456789", "consent": True})
    assert r.status_code == 200
    tok = r.json()["token"]
    assert pub.post(f"/api/s/o-{cid}/start", json={"name": "Ravi", "phone": "9123456789", "consent": True}).json()["token"] == tok  # same phone resumes, no second attempt
    rc.post(f"/api/hub/campaigns/{cid}/status", json={"status": "closed"})
    assert pub.get(f"/api/s/o-{cid}").status_code == 410


def test_team_viewer_pipeline_and_isolation():
    owner = client()
    reg(owner, "o1@example.com", "recruiter")
    org = owner.get("/api/hub/org").json()
    viewer = client()
    reg(viewer, "v1@example.com", "recruiter", org["viewer_code"])
    assert viewer.get("/api/hub/pipeline").status_code == 200
    assert viewer.post("/api/hub/pipeline", json={"name": "X"}).status_code == 403
    assert owner.post("/api/hub/pipeline", json={"name": "Asha", "stage": "Screened"}).status_code == 200
    items = viewer.get("/api/hub/pipeline").json()["items"]
    assert items and items[0]["stage"] == "Screened"
    other = client()
    reg(other, "o2@example.com", "recruiter")
    assert other.get("/api/hub/pipeline").json()["items"] == []  # another company sees nothing
    key = owner.post("/api/hub/org/apikey").json()["api_key"]
    assert client().get("/api/v1/results", headers={"x-api-key": key}).status_code == 200
    assert client().get("/api/v1/results", headers={"x-api-key": "mr_bad"}).status_code == 401
    assert any(a["action"] == "api_key_created" for a in owner.get("/api/hub/audit").json()["items"])
    assert owner.get("/api/hub/org").json()["invite_code"] and viewer.get("/api/hub/org").json()["invite_code"] is None


def test_practice_and_status():
    c = client()
    g = c.get("/api/practice/quiz").json()
    assert "a" not in g["items"][0]
    r = c.post("/api/practice/quiz", json={"seed": g["seed"], "answers": [0] * 10}).json()
    assert r["total"] == 10 and len(r["correct_answers"]) == 10
    assert c.get("/api/status").json()["status"] == "ok"
