import os
import tempfile

os.environ.pop("NEBIUS_API_KEY", None)
os.environ.pop("DATABASE_URL", None)
os.environ["RATE_LIMIT_PER_MIN"] = "100000"
os.environ["AUTH_RATE_PER_MIN"] = "100000"
os.environ["SIGNUPS_PER_DAY"] = "100000"
os.environ["AI_DAILY_PER_IP"] = "100000"
os.environ["INTERVIEWPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "acc.sqlite3")

from fastapi.testclient import TestClient

from app import accounts
from app.main import app

accounts.SQLITE_PATH = os.environ["INTERVIEWPILOT_DB"]


def fresh():
    return TestClient(app)


def test_guest_gets_401_on_history_but_features_work():
    c = fresh()
    assert c.get("/api/history").status_code == 401
    assert c.get("/api/auth/me").json()["user"] is None
    assert c.get("/health").status_code == 200


def test_register_login_logout_flow():
    c = fresh()
    r = c.post("/api/auth/register", json={"email": "A@Example.com", "password": "longenough1"})
    assert r.status_code == 200 and r.json()["user"]["email"] == "a@example.com"
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()
    assert c.get("/api/auth/me").json()["user"]["email"] == "a@example.com"
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").json()["user"] is None
    assert c.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "longenough1"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "a@example.com", "password": "longenough1"}).status_code == 200


def test_register_validation_and_duplicates():
    c = fresh()
    assert c.post("/api/auth/register", json={"email": "bad", "password": "longenough1"}).status_code == 400
    assert c.post("/api/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 400
    assert c.post("/api/auth/register", json={"email": "b@example.com", "password": "longenough1"}).status_code == 200
    assert c.post("/api/auth/register", json={"email": "B@example.com", "password": "longenough1"}).status_code == 400


def test_history_save_list_get_delete_and_isolation():
    a, b = fresh(), fresh()
    a.post("/api/auth/register", json={"email": "h1@example.com", "password": "longenough1"})
    b.post("/api/auth/register", json={"email": "h2@example.com", "password": "longenough1"})
    s = a.post("/api/history", json={"kind": "prep", "title": "QA pack", "data": {"questions": [1, 2]}})
    assert s.status_code == 200
    iid = s.json()["id"]
    assert [i["title"] for i in a.get("/api/history").json()["items"]] == ["QA pack"]
    assert a.get(f"/api/history/{iid}").json()["data"] == {"questions": [1, 2]}
    assert b.get(f"/api/history/{iid}").status_code == 404  # other users cannot read it
    assert b.delete(f"/api/history/{iid}").status_code == 404
    assert b.get("/api/history").json()["items"] == []
    assert a.post("/api/history", json={"kind": "bogus", "title": "x", "data": {}}).status_code == 400
    assert a.delete(f"/api/history/{iid}").status_code == 200
    assert a.get(f"/api/history/{iid}").status_code == 404


def test_history_size_limit_and_cap(monkeypatch):
    a = fresh()
    a.post("/api/auth/register", json={"email": "h3@example.com", "password": "longenough1"})
    assert a.post("/api/history", json={"kind": "prep", "title": "big", "data": {"x": "y" * 130000}}).status_code == 400
    monkeypatch.setattr(accounts, "MAX_HISTORY_PER_USER", 3)
    for i in range(5):
        a.post("/api/history", json={"kind": "resume", "title": f"r{i}", "data": {"i": i}})
    assert len(a.get("/api/history").json()["items"]) == 3


def test_delete_account_removes_everything():
    a = fresh()
    a.post("/api/auth/register", json={"email": "gone@example.com", "password": "longenough1"})
    a.post("/api/history", json={"kind": "prep", "title": "t", "data": {}})
    assert a.delete("/api/auth/account").status_code == 200
    assert a.get("/api/auth/me").json()["user"] is None
    assert a.post("/api/auth/login", json={"email": "gone@example.com", "password": "longenough1"}).status_code == 401


def test_auth_rate_limit(monkeypatch):
    from app import main
    from app.guard import RateLimiter

    monkeypatch.setattr(main, "_auth_limiter", RateLimiter(limit=2, window=60))
    c = fresh()
    codes = [c.post("/api/auth/login", json={"email": "x@example.com", "password": "nope"}).status_code for _ in range(4)]
    assert codes[:2] == [401, 401] and 429 in codes[2:]
