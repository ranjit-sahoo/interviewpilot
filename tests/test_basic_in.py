import os

os.environ.pop("NEBIUS_API_KEY", None)
os.environ["RATE_LIMIT_PER_MIN"] = "100000"
os.environ["AUTH_RATE_PER_MIN"] = "100000"
os.environ["SIGNUPS_PER_DAY"] = "100000"
os.environ["AI_DAILY_PER_IP"] = "100000"
import tempfile

os.environ["INTERVIEWPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "b.sqlite3")

from fastapi.testclient import TestClient

from app import basic_in, bank, market
from app.basic_in_data import DATA
from app.main import app

c = TestClient(app)
IN = {"cf-ipcountry": "IN"}
US = {"cf-ipcountry": "US"}
R12 = "Sunita Devi. 12th pass (Commerce), Patna, Bihar. Skills: Hindi, basic English, MS Word, typing. No work experience."
BA = "Rahul Kumar. B.A. (Hons) graduate, Lucknow. Typing, MS Office, good communication. Fresher."
ENG = "Asha Rao. B.Tech Computer Science, Bengaluru. Java, Spring, SQL. 2 years experience."
BCOM_PLAIN = "Ravi Singh. B.Com graduate from Jaipur, Rajasthan, with Tally and Excel skills. Fresher."


def test_basic_detection_india_only():
    assert market.is_basic_in("India", R12, "BPO executive")
    assert market.is_basic_in("India", BA, "Accenture associate")
    assert market.is_basic_in("India", BCOM_PLAIN, "Customer support")
    assert not market.is_basic_in("India", ENG, "Java Developer")
    assert not market.is_basic_in("India", "", "Customer support")
    assert market.is_basic_in("India", "", "Customer support", "basic")
    assert not market.is_basic_in("India", R12, "BPO", "experienced")
    assert not market.is_basic_in("India", "Rahul. BCA graduate. Python, SQL.", "Python Developer")
    # the US and other markets never use it, even when asked
    assert not market.is_basic_in("US", R12, "BPO", "basic")
    assert not market.is_basic_in("Other", R12, "BPO", "basic")


def test_pick_always_starts_with_intro_and_why_and_has_no_duplicates():
    for role in ("BPO Customer Support", "Air Hostess", "Hotel Front Desk", "Airport Ground Staff", "Associate"):
        for n in (3, 5, 8):
            qs = basic_in.pick(n, role)
            assert len(qs) == n
            assert qs[0]["question"] == "Tell me about yourself."
            assert "why" in qs[1]["question"].lower()
            texts = [basic_in._norm(q["question"]) for q in qs]
            assert len(set(texts)) == n
            assert all(q["ref"] for q in qs)


def test_categories():
    assert basic_in.category("Air Hostess / Cabin Crew") == "cabin"
    assert basic_in.category("Airport Ground Staff") == "airport"
    assert basic_in.category("Hotel Front Desk Executive") == "hotel"
    assert basic_in.category("Associate", "We need a hotel receptionist") == "hotel"
    assert basic_in.category("Associate") == "bpo"


def test_india_basic_interview_uses_his_set_and_hides_answers():
    r = c.post("/api/session", json={"resume": R12, "role": "BPO Customer Support", "jd": "", "country": "India", "level": "auto", "followups": False, "count": 5}, headers=IN)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["basic"] is True and d["level"] == "basic" and d["total"] == 5
    assert d["question"]["question"] == "Tell me about yourself."
    assert "ref" not in d["question"] and "tip" not in d["question"]
    sid = d["session_id"]
    seen = [d["question"]["question"]]
    for _ in range(5):
        a = c.post(f"/api/session/{sid}/answer", json={"answer": "I am a quick learner and I want to start my career here."}, headers=IN)
        assert a.status_code == 200, a.text
        j = a.json()
        if j["finished"]:
            break
        assert "ref" not in j["next_question"]
        seen.append(j["next_question"]["question"])
    assert len(seen) == 5
    bank_qs = {basic_in._norm(o["q"]) for o in DATA}
    assert all(basic_in._norm(q) in bank_qs for q in seen)  # every question came from the reviewed set


def test_us_and_it_flows_unchanged():
    for headers, resume, level in ((US, R12, "basic"), (US, R12, "auto"), (IN, ENG, "auto")):
        r = c.post("/api/session", json={"resume": resume, "role": "QA Engineer", "jd": "", "country": "US", "level": level, "followups": False, "count": 5}, headers=headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["basic"] is False and d["level"] != "basic"


def test_prep_pack_basic_vs_it():
    r = c.post("/api/prep", json={"resume": R12, "role": "Hotel Front Desk", "jd": "", "country": "India"}, headers=IN)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["basic"] is True and len(d["questions"]) == 10 and d["coding_profile"] is False
    r = c.post("/api/prep", json={"resume": R12, "role": "Hotel Front Desk", "jd": "", "country": "US"}, headers=US)
    assert not r.json().get("basic")


def test_bank_has_new_roles():
    roles = bank.roles()
    for name in ("BPO / Call Centre", "Cabin Crew / Air Hostess", "Hotel & Hospitality", "Airport Ground Staff"):
        assert name in roles
    assert bank.curated("air hostess")["role"] == "Cabin Crew / Air Hostess"
    assert bank.curated("hotel front desk")["role"] == "Hotel & Hospitality"
    assert bank.curated("airport ground staff")["role"] == "Airport Ground Staff"
    assert bank.curated("call centre")["role"] == "BPO / Call Centre"
    assert bank.curated("onboarding specialist")["role"] != "Airport Ground Staff"
    assert len(bank.curated("bpo")["questions"]) >= 50
    assert bank.curated("QA automation engineer")["matched"]  # existing roles unaffected


def test_no_personal_details_left():
    blob = " ".join(o["q"] + o["ref"] + o["tip"] for o in DATA).lower()
    for bad in ("kankinara", "hostel", "republic day", "2012", " java "):
        assert bad not in blob
