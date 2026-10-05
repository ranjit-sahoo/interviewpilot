"""Privacy-friendly first-party visitor counts. Free, no third-party script, no cookies, no raw IPs.

What is stored: per-day counters (page views, a few feature hits) and a per-day one-way hash used only to count
unique visitors. The hash mixes the day, IP and browser string with a server-side salt, so it cannot be turned
back into an IP and cannot be linked across days. Bots and uptime checks are skipped.
"""
import hashlib
import html
import os
import re
import threading
import time

from app import accounts
from app.guard import client_key

_BOT = re.compile(r"bot|crawl|spider|slurp|uptime|monitor|curl|wget|python-requests|httpx|go-http|node-fetch|headless|preview|facebookexternalhit|render", re.I)
# POST endpoint -> counter name. Only successful calls are counted.
_FEATURES = {
    "/api/session": "interview_start",
    "/api/resume/review": "resume_review",
    "/api/match": "jd_match",
    "/api/prep": "prep_pack",
    "/api/prep/coding": "coding_prep",
    "/api/negotiation": "negotiation",
    "/api/recruiter/screen": "recruiter_screen",
    "/api/bank": "question_bank",
    "/api/star": "star_builder",
    "/api/company-brief": "company_brief",
    "/api/builder/polish": "resume_builder",
    "/api/auth/register": "signup",
    "/api/waitlist": "waitlist",
}
LABELS = {
    "pageview": "Page views",
    "interview_start": "Interviews started",
    "resume_review": "Resume reviews",
    "jd_match": "JD matches",
    "prep_pack": "Prep packs",
    "coding_prep": "Coding prep",
    "negotiation": "Salary negotiations",
    "recruiter_screen": "Recruiter screens",
    "question_bank": "Question bank",
    "star_builder": "STAR stories",
    "company_brief": "Company briefs",
    "resume_builder": "Resume builder",
    "signup": "Sign-ups",
    "waitlist": "Waitlist",
}
_salt = hashlib.sha256((accounts.DATABASE_URL or "local").encode()).hexdigest()
_ready = False
_ready_lock = threading.Lock()


def _ensure(c):
    global _ready
    if _ready:
        return
    with _ready_lock:
        c.run("CREATE TABLE IF NOT EXISTS visit_counts (day TEXT NOT NULL, metric TEXT NOT NULL, n INTEGER NOT NULL, PRIMARY KEY (day, metric))")
        c.run("CREATE TABLE IF NOT EXISTS visit_uniques (day TEXT NOT NULL, vhash TEXT NOT NULL, PRIMARY KEY (day, vhash))")
        _ready = True


def _day(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts if ts is not None else time.time()))


def classify(method: str, path: str, status: int) -> str | None:
    """Which counter (if any) a finished request belongs to."""
    if status >= 400:
        return None
    if method == "GET" and path == "/":
        return "pageview"
    if method == "POST":
        return _FEATURES.get(path)
    return None


def record(metric: str, ip: str, ua: str) -> None:
    """Never raises: analytics must not break a request."""
    try:
        if _BOT.search(ua or ""):
            return
        day = _day()
        vh = hashlib.sha256(f"{_salt}|{day}|{ip}|{ua}".encode()).hexdigest()[:20]
        with accounts.Conn() as c:
            _ensure(c)
            c.run("INSERT INTO visit_counts (day, metric, n) VALUES (?, ?, 1) ON CONFLICT (day, metric) DO UPDATE SET n = visit_counts.n + 1", (day, metric))
            if metric == "pageview":
                c.run("INSERT INTO visit_uniques (day, vhash) VALUES (?, ?) ON CONFLICT (day, vhash) DO NOTHING", (day, vh))
    except Exception:
        pass


def summary(days: int = 30) -> dict:
    since = _day(time.time() - days * 86400)
    with accounts.Conn() as c:
        _ensure(c)
        counts = c.run("SELECT day, metric, n FROM visit_counts WHERE day >= ? ORDER BY day", (since,))
        uniq = c.run("SELECT day, COUNT(*) AS u FROM visit_uniques WHERE day >= ? GROUP BY day ORDER BY day", (since,))
    per_day: dict = {}
    totals: dict = {}
    for r in counts:
        per_day.setdefault(r["day"], {})[r["metric"]] = int(r["n"])
        totals[r["metric"]] = totals.get(r["metric"], 0) + int(r["n"])
    for r in uniq:
        per_day.setdefault(r["day"], {})["visitors"] = int(r["u"])
    return {
        "days": days,
        "totals": totals,
        "visitor_days": sum(int(r["u"]) for r in uniq),
        "per_day": [{"day": d, **per_day[d]} for d in sorted(per_day, reverse=True)],
    }


def render_html(s: dict) -> str:
    e = html.escape
    cards = "".join(
        f"<div class='c'><b>{int(s['totals'].get(k, 0))}</b><span>{e(v)}</span></div>" for k, v in LABELS.items() if k in ("pageview", "interview_start", "resume_review", "prep_pack", "signup", "waitlist")
    )
    cols = list(LABELS)
    head = "".join(f"<th>{e(LABELS[k])}</th>" for k in cols)
    rows = "".join(
        f"<tr><td>{e(r['day'])}</td><td>{r.get('visitors', 0)}</td>" + "".join(f"<td>{r.get(k, 0)}</td>" for k in cols) + "</tr>"
        for r in s["per_day"]
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Usage - InterviewPilot</title><meta name='robots' content='noindex'>"
        "<style>body{font:15px system-ui,sans-serif;margin:24px;max-width:1100px;color:#111}h1{font-size:22px}"
        ".g{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}.c{border:1px solid #ddd;border-radius:10px;padding:12px 16px;min-width:120px}"
        ".c b{display:block;font-size:26px}.c span{color:#555;font-size:13px}table{border-collapse:collapse;width:100%;font-size:13px}"
        "th,td{border-bottom:1px solid #eee;padding:6px 8px;text-align:right}th:first-child,td:first-child{text-align:left}"
        ".w{overflow-x:auto}p{color:#555;font-size:13px}</style></head><body>"
        f"<h1>InterviewPilot usage (last {int(s['days'])} days, UTC)</h1>"
        f"<div class='g'>{cards}<div class='c'><b>{int(s['visitor_days'])}</b><span>Unique visitor-days</span></div></div>"
        f"<div class='w'><table><thead><tr><th>Day</th><th>Visitors</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>"
        "<p>First-party counts only: no cookies, no third-party scripts, no IP addresses stored. A visitor is counted once per day "
        "using a one-way hash that cannot be reversed or linked across days. Bots and uptime checks are skipped.</p></body></html>"
    )


def install(app) -> None:
    """Hook the counters and the public /stats page into the app."""
    import asyncio

    from fastapi import Request
    from fastapi.responses import HTMLResponse

    @app.middleware("http")
    async def _count(request: Request, call_next):
        resp = await call_next(request)
        metric = classify(request.method, request.url.path, resp.status_code)
        if metric:
            asyncio.get_running_loop().run_in_executor(None, record, metric, client_key(request), request.headers.get("user-agent", ""))
        return resp

    @app.get("/api/stats")
    def api_stats():
        return summary()

    @app.get("/stats", response_class=HTMLResponse)
    def stats_page():
        return HTMLResponse(render_html(summary()))
