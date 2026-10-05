import os
import tempfile
import time

os.environ.pop("NEBIUS_API_KEY", None)
os.environ.pop("DATABASE_URL", None)
os.environ["RATE_LIMIT_PER_MIN"] = "100000"
os.environ["AI_DAILY_PER_IP"] = "100000"
os.environ["INTERVIEWPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "an.sqlite3")

from fastapi.testclient import TestClient

from app import accounts, analytics
from app.main import app

accounts.SQLITE_PATH = os.environ["INTERVIEWPILOT_DB"]
c = TestClient(app)


def _wait(metric, want, tries=40):
    for _ in range(tries):
        if analytics.summary()["totals"].get(metric, 0) >= want:
            return True
        time.sleep(0.05)
    return False


def test_classify():
    assert analytics.classify("GET", "/", 200) == "pageview"
    assert analytics.classify("HEAD", "/", 200) is None
    assert analytics.classify("GET", "/health", 200) is None
    assert analytics.classify("POST", "/api/session", 200) == "interview_start"
    assert analytics.classify("POST", "/api/session", 429) is None
    assert analytics.classify("GET", "/static/x.png", 200) is None


def test_pageviews_unique_and_stats_page():
    h = {"user-agent": "Mozilla/5.0 (X11) Chrome/120"}
    for _ in range(3):
        assert c.get("/", headers=h).status_code == 200
    assert _wait("pageview", 3)
    s = analytics.summary()
    assert s["totals"]["pageview"] == 3
    assert s["visitor_days"] == 1  # same IP + browser counts once per day
    page = c.get("/stats")
    assert page.status_code == 200 and "Page views" in page.text
    j = c.get("/api/stats").json()
    assert j["totals"]["pageview"] == 3
    assert "ip" not in str(j).lower()


def test_bots_and_uptime_are_skipped():
    before = analytics.summary()["totals"].get("pageview", 0)
    c.get("/", headers={"user-agent": "UptimeRobot/2.0"})
    c.get("/", headers={"user-agent": "Googlebot/2.1"})
    time.sleep(0.4)
    assert analytics.summary()["totals"].get("pageview", 0) == before


def test_record_never_raises():
    analytics.record("pageview", "1.2.3.4", None)
