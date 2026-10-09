"""Recruiter hub, screening links and skill tests. Everything here is rule-based (no AI calls, no paid services)."""
import csv
import hashlib
import io
import json
import os
import re
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app import accounts, entitlements, hubdata, hubparse, screening
from app.guard import RateLimiter, client_key, rate_limit

router = APIRouter()
STATIC = os.path.join(os.path.dirname(__file__), "static")
COOKIE = "ip_session"
STARTED = time.time()
STAGES = ["New", "Screened", "Interview", "Offer", "Rejected"]
_scr_limiter = RateLimiter(limit=600, window=60.0)  # shared office networks: many candidates behind one IP


def scr_limit(request: Request):
    if not _scr_limiter.check(client_key(request)):
        raise HTTPException(429, "Too many requests. Please wait a minute and try again.")


def _now() -> float:
    return time.time()


# ---------------- auth helpers ----------------
def rec(request: Request) -> dict:
    u = accounts.user_for(request.cookies.get(COOKIE))
    if not u or u.get("role") != "recruiter" or not u.get("org_id"):
        raise HTTPException(403, "This needs a recruiter account. Create one (free) from the menu with the Recruiter option.")
    return u


def rec_write(request: Request) -> dict:
    u = rec(request)
    if u.get("org_role") == "viewer":
        raise HTTPException(403, "Your team role is Viewer, so you can look but not change anything.")
    return u


def owner(request: Request) -> dict:
    u = rec(request)
    if u.get("org_role") != "owner":
        raise HTTPException(403, "Only the company owner can do this.")
    return u


def audit(c, u: dict, action: str, target: str = ""):
    c.run("INSERT INTO audit (id, org_id, user_email, action, target, ts) VALUES (?, ?, ?, ?, ?, ?)",
          (uuid.uuid4().hex, u["org_id"], u["email"], action[:60], (target or "")[:200], _now()))


_last_purge = 0.0


def purge():
    """Auto-delete finished attempts whose retention period has passed. Runs lazily, at most every 10 minutes."""
    global _last_purge
    if _now() - _last_purge < 600:
        return
    _last_purge = _now()
    with accounts.Conn() as c:
        c.run("DELETE FROM attempts WHERE delete_after IS NOT NULL AND delete_after < ?", (_now(),))
        c.run("DELETE FROM attempts WHERE status<>'done' AND created < ?", (_now() - 90 * 86400,))


def phone_norm(p: str) -> str:
    d = re.sub(r"\D", "", p or "")
    d = d[2:] if d.startswith("00") else d
    if len(d) == 10 and d[0] in "6789":
        return "91" + d
    if len(d) == 10 and d.startswith("05"):
        return "971" + d[1:]
    if len(d) == 11 and d.startswith("0"):
        return "91" + d[1:]
    return d


# ---------------- models ----------------
class ScreenIn(BaseModel):
    resumes: list[dict] = Field(max_length=100)
    must: list[str] = Field(default_factory=list, max_length=40)
    nice: list[str] = Field(default_factory=list, max_length=40)
    min_years: float = Field(0, ge=0, le=40)
    location: str = Field("", max_length=80)


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role_title: str = Field("", max_length=80)
    pool: str = "bpo"
    modules: list[str] = Field(default_factory=lambda: ["voice"], max_length=5)
    n_questions: int = Field(6, ge=3, le=10)
    secs: int = Field(90, ge=30, le=180)
    expires_days: int = Field(14, ge=1, le=60)
    lang: str = "en"
    retention_days: int = Field(30, ge=7, le=90)
    open_link: bool = True


class InviteIn(BaseModel):
    candidates: list[dict] = Field(max_length=200)


class PipeIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: str = Field("", max_length=30)
    email: str = Field("", max_length=120)
    role_title: str = Field("", max_length=80)
    stage: str = "New"
    notes: str = Field("", max_length=1500)
    score: float | None = None
    source: str = Field("manual", max_length=40)


class PipePatch(BaseModel):
    stage: str | None = None
    notes: str | None = Field(None, max_length=1500)


class OrgPatch(BaseModel):
    name: str | None = Field(None, max_length=80)
    brand_color: str | None = Field(None, max_length=9)
    logo: str | None = Field(None, max_length=90000)


class AuditIn(BaseModel):
    action: str = Field(max_length=60)
    target: str = Field("", max_length=200)


# ---------------- recruiter: resume screener ----------------
@router.post("/api/hub/screen", dependencies=[Depends(rate_limit)])
def hub_screen(body: ScreenIn, u=Depends(rec_write)):
    lim = entitlements.limit(u, "resumes_per_run") or 100
    res = [{"name": str(r.get("name", ""))[:80], "text": str(r.get("text", ""))[:60000]} for r in body.resumes[:lim]]
    rows = hubparse.rank(res, body.must, body.nice, body.min_years, body.location)
    with accounts.Conn() as c:
        audit(c, u, "screen_resumes", f"{len(res)} resumes")
    return {"results": rows, "count": len(rows)}


# ---------------- recruiter: campaigns ----------------
def _camp_public(r: dict) -> dict:
    return {"id": r["id"], "name": r["name"], "role_title": r["role_title"], "pool": r["pool"], "modules": json.loads(r["modules"]),
            "n_questions": r["n_questions"], "secs": r["secs"], "expires": r["expires"], "status": r["status"], "lang": r["lang"],
            "retention_days": r["retention_days"], "open_link": bool(r["open_link"]), "created": r["created"]}


@router.get("/api/hub/options")
def hub_options():
    return {"pools": hubdata.POOL_LABELS, "modules": hubdata.MODULE_LABELS, "stages": STAGES}


@router.post("/api/hub/campaigns", dependencies=[Depends(rate_limit)])
def camp_create(body: CampaignIn, u=Depends(rec_write)):
    mods = [m for m in body.modules if m in hubdata.MODULE_LABELS]
    if not mods:
        raise HTTPException(400, "Pick at least one test.")
    pool = body.pool if body.pool in hubdata.POOL_LABELS else "bpo"
    lang = body.lang if body.lang in ("en", "hi", "hinglish", "ar") else "en"
    cid = uuid.uuid4().hex[:10]
    with accounts.Conn() as c:
        n = c.run("SELECT COUNT(*) AS n FROM campaigns WHERE org_id=?", (u["org_id"],))[0]["n"]
        if n >= (entitlements.limit(u, "campaigns") or 100):
            raise HTTPException(403, "Campaign limit reached for your plan.")
        c.run("INSERT INTO campaigns (id, org_id, created_by, name, role_title, pool, modules, n_questions, secs, expires, status, lang, retention_days, open_link, created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (cid, u["org_id"], u["id"], body.name.strip(), body.role_title.strip() or hubdata.POOL_LABELS[pool], pool, json.dumps(mods), body.n_questions, body.secs,
               _now() + body.expires_days * 86400, "open", lang, body.retention_days, 1 if body.open_link else 0, _now()))
        audit(c, u, "campaign_created", body.name)
        r = c.run("SELECT * FROM campaigns WHERE id=?", (cid,))[0]
    return _camp_public(r)


def _mine(c, u, cid: str) -> dict:
    r = c.run("SELECT * FROM campaigns WHERE id=? AND org_id=?", (cid, u["org_id"]))
    if not r:
        raise HTTPException(404, "Campaign not found.")
    return r[0]


@router.get("/api/hub/campaigns", dependencies=[Depends(rate_limit)])
def camp_list(u=Depends(rec)):
    purge()
    with accounts.Conn() as c:
        rows = c.run("SELECT * FROM campaigns WHERE org_id=? ORDER BY created DESC LIMIT 200", (u["org_id"],))
        counts = {r["campaign_id"]: r for r in c.run(
            "SELECT campaign_id, COUNT(*) AS total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done, AVG(score) AS avg FROM attempts WHERE campaign_id IN (SELECT id FROM campaigns WHERE org_id=?) GROUP BY campaign_id", (u["org_id"],))}
    out = []
    for r in rows:
        d = _camp_public(r)
        k = counts.get(r["id"], {})
        d.update({"total": k.get("total", 0) or 0, "done": k.get("done", 0) or 0, "avg": round(k["avg"]) if k.get("avg") is not None else None})
        out.append(d)
    return {"campaigns": out}


@router.get("/api/hub/campaigns/{cid}", dependencies=[Depends(rate_limit)])
def camp_get(cid: str, u=Depends(rec)):
    with accounts.Conn() as c:
        camp = _mine(c, u, cid)
        rows = c.run("SELECT * FROM attempts WHERE campaign_id=? ORDER BY COALESCE(score,-1) DESC, created", (cid,))
        audit(c, u, "results_viewed", camp["name"])
    out = []
    for a in rows:
        d = json.loads(a["data"] or "{}")
        mods = {}
        for m in ("typing", "reading", "quiz", "apt"):
            if m in d:
                mods[m] = d[m]
        out.append({"id": a["id"], "token": a["token"], "name": a["name"], "phone": a["phone"], "status": a["status"], "score": None if a["score"] is None else round(a["score"]),
                    "started": a["started"], "finished": a["finished"], "signals": d.get("signals", []), "modules": mods,
                    "voice": [{"q": v.get("q"), "text": v.get("text"), "score": v.get("score"), "notes": v.get("notes"), "followup": v.get("fu_text"), "fu_text_answer": v.get("fu_answer"),
                               "secs": v.get("secs"), "think": v.get("think"), "pauses": v.get("pauses"), "late": v.get("late")} for v in d.get("voice", [])],
                    "leaves": d.get("leaves", 0)})
    return {"campaign": _camp_public(camp), "attempts": out}


@router.post("/api/hub/campaigns/{cid}/status", dependencies=[Depends(rate_limit)])
def camp_status(cid: str, body: dict, u=Depends(rec_write)):
    st = body.get("status")
    if st not in ("open", "closed"):
        raise HTTPException(400, "Status must be open or closed.")
    with accounts.Conn() as c:
        camp = _mine(c, u, cid)
        c.run("UPDATE campaigns SET status=? WHERE id=?", (st, cid))
        audit(c, u, "campaign_" + st, camp["name"])
    return {"ok": True}


@router.delete("/api/hub/campaigns/{cid}", dependencies=[Depends(rate_limit)])
def camp_delete(cid: str, u=Depends(rec_write)):
    with accounts.Conn() as c:
        camp = _mine(c, u, cid)
        c.run("DELETE FROM attempts WHERE campaign_id=?", (cid,))
        c.run("DELETE FROM campaigns WHERE id=?", (cid,))
        audit(c, u, "campaign_deleted", camp["name"])
    return {"ok": True}


@router.post("/api/hub/campaigns/{cid}/invite", dependencies=[Depends(rate_limit)])
def camp_invite(cid: str, body: InviteIn, u=Depends(rec_write)):
    out = []
    with accounts.Conn() as c:
        camp = _mine(c, u, cid)
        if camp["status"] != "open":
            raise HTTPException(400, "This campaign is closed.")
        have = c.run("SELECT COUNT(*) AS n FROM attempts WHERE campaign_id=?", (cid,))[0]["n"]
        cap = entitlements.limit(u, "invites_per_campaign") or 200
        existing = {a["phone"]: a["token"] for a in c.run("SELECT phone, token FROM attempts WHERE campaign_id=?", (cid,))}
        for cand in body.candidates:
            name = str(cand.get("name", "")).strip()[:80] or "Candidate"
            ph = phone_norm(str(cand.get("phone", "")))
            if ph and ph in existing:
                out.append({"name": name, "phone": ph, "token": existing[ph], "existing": True})
                continue
            if have >= cap:
                raise HTTPException(403, "Invite limit reached for this campaign.")
            tok = secrets.token_urlsafe(8)
            c.run("INSERT INTO attempts (id, campaign_id, token, name, phone, status, data, created) VALUES (?,?,?,?,?,?,?,?)",
                  (uuid.uuid4().hex, cid, tok, name, ph, "invited", "{}", _now()))
            have += 1
            if ph:
                existing[ph] = tok
            out.append({"name": name, "phone": ph, "token": tok})
        audit(c, u, "invites_created", f"{camp['name']}: {len(out)}")
    return {"invites": out}


# ---------------- recruiter: pipeline ----------------
@router.get("/api/hub/pipeline", dependencies=[Depends(rate_limit)])
def pipe_list(u=Depends(rec)):
    with accounts.Conn() as c:
        rows = c.run("SELECT * FROM pipeline WHERE org_id=? ORDER BY updated DESC LIMIT 1000", (u["org_id"],))
    return {"stages": STAGES, "items": rows}


@router.post("/api/hub/pipeline", dependencies=[Depends(rate_limit)])
def pipe_add(body: PipeIn, u=Depends(rec_write)):
    pid = uuid.uuid4().hex
    stage = body.stage if body.stage in STAGES else "New"
    with accounts.Conn() as c:
        if c.run("SELECT COUNT(*) AS n FROM pipeline WHERE org_id=?", (u["org_id"],))[0]["n"] >= 1000:
            raise HTTPException(403, "Pipeline is full (1000 candidates).")
        c.run("INSERT INTO pipeline (id, org_id, name, phone, email, role_title, stage, notes, score, source, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (pid, u["org_id"], body.name.strip(), phone_norm(body.phone), body.email.strip().lower(), body.role_title.strip(), stage, body.notes, body.score, body.source, _now(), _now()))
        audit(c, u, "pipeline_add", body.name)
    return {"id": pid}


@router.patch("/api/hub/pipeline/{pid}", dependencies=[Depends(rate_limit)])
def pipe_patch(pid: str, body: PipePatch, u=Depends(rec_write)):
    with accounts.Conn() as c:
        r = c.run("SELECT * FROM pipeline WHERE id=? AND org_id=?", (pid, u["org_id"]))
        if not r:
            raise HTTPException(404, "Not found.")
        stage = body.stage if body.stage in STAGES else r[0]["stage"]
        notes = r[0]["notes"] if body.notes is None else body.notes
        c.run("UPDATE pipeline SET stage=?, notes=?, updated=? WHERE id=?", (stage, notes, _now(), pid))
        if stage != r[0]["stage"]:
            audit(c, u, "pipeline_move", f"{r[0]['name']} -> {stage}")
    return {"ok": True}


@router.delete("/api/hub/pipeline/{pid}", dependencies=[Depends(rate_limit)])
def pipe_del(pid: str, u=Depends(rec_write)):
    with accounts.Conn() as c:
        r = c.run("SELECT name FROM pipeline WHERE id=? AND org_id=?", (pid, u["org_id"]))
        if r:
            c.run("DELETE FROM pipeline WHERE id=?", (pid,))
            audit(c, u, "pipeline_delete", r[0]["name"])
    return {"ok": True}


# ---------------- recruiter: company, team, audit, API key, dashboard ----------------
@router.get("/api/hub/org", dependencies=[Depends(rate_limit)])
def org_get(u=Depends(rec)):
    with accounts.Conn() as c:
        o = c.run("SELECT * FROM orgs WHERE id=?", (u["org_id"],))
        o = o[0] if o else {"name": "", "brand_color": "#5b8cff", "logo": "", "api_key_hash": None, "invite_code": "", "viewer_code": ""}
        team = c.run("SELECT id, email, org_role FROM users WHERE org_id=? ORDER BY created", (u["org_id"],))
    is_owner = u["org_role"] == "owner"
    return {"name": o["name"], "brand_color": o["brand_color"], "logo": o["logo"], "org_role": u["org_role"], "plan": u.get("plan", "free"),
            "has_api_key": bool(o["api_key_hash"]), "invite_code": o["invite_code"] if is_owner else None, "viewer_code": o["viewer_code"] if is_owner else None,
            "team": [{"id": t["id"], "email": t["email"], "org_role": t["org_role"]} for t in team]}


@router.patch("/api/hub/org", dependencies=[Depends(rate_limit)])
def org_patch(body: OrgPatch, u=Depends(owner)):
    with accounts.Conn() as c:
        if body.name is not None:
            c.run("UPDATE orgs SET name=? WHERE id=?", (body.name.strip(), u["org_id"]))
        if body.brand_color is not None:
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", body.brand_color):
                raise HTTPException(400, "Colour must look like #5b8cff.")
            c.run("UPDATE orgs SET brand_color=? WHERE id=?", (body.brand_color, u["org_id"]))
        if body.logo is not None:
            if body.logo and not re.fullmatch(r"data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+", body.logo):
                raise HTTPException(400, "Logo must be a small PNG, JPEG or WebP image.")
            c.run("UPDATE orgs SET logo=? WHERE id=?", (body.logo, u["org_id"]))
        audit(c, u, "company_settings_changed", "")
    return {"ok": True}


@router.post("/api/hub/org/rotate-codes", dependencies=[Depends(rate_limit)])
def org_rotate(u=Depends(owner)):
    a, b = "R" + uuid.uuid4().hex[:10], "V" + uuid.uuid4().hex[:10]
    with accounts.Conn() as c:
        c.run("UPDATE orgs SET invite_code=?, viewer_code=? WHERE id=?", (a, b, u["org_id"]))
        audit(c, u, "invite_codes_rotated", "")
    return {"invite_code": a, "viewer_code": b}


@router.delete("/api/hub/org/team/{uid}", dependencies=[Depends(rate_limit)])
def org_remove(uid: str, u=Depends(owner)):
    if uid == u["id"]:
        raise HTTPException(400, "The owner cannot be removed.")
    with accounts.Conn() as c:
        r = c.run("SELECT email FROM users WHERE id=? AND org_id=?", (uid, u["org_id"]))
        if r:
            c.run("UPDATE users SET org_id=NULL, org_role=NULL, role='candidate' WHERE id=?", (uid,))
            c.run("DELETE FROM auth_sessions WHERE user_id=?", (uid,))
            audit(c, u, "member_removed", r[0]["email"])
    return {"ok": True}


@router.post("/api/hub/org/apikey", dependencies=[Depends(rate_limit)])
def org_apikey(u=Depends(owner)):
    if not entitlements.limit(u, "api"):
        raise HTTPException(403, "API access is not part of your plan.")
    key = "mr_" + secrets.token_urlsafe(24)
    with accounts.Conn() as c:
        c.run("UPDATE orgs SET api_key_hash=? WHERE id=?", (hashlib.sha256(key.encode()).hexdigest(), u["org_id"]))
        audit(c, u, "api_key_created", "")
    return {"api_key": key, "note": "Copy it now. It is shown only once."}


@router.get("/api/hub/audit", dependencies=[Depends(rate_limit)])
def audit_get(u=Depends(rec)):
    with accounts.Conn() as c:
        rows = c.run("SELECT user_email, action, target, ts FROM audit WHERE org_id=? ORDER BY ts DESC LIMIT 200", (u["org_id"],))
    return {"items": rows}


@router.post("/api/hub/audit", dependencies=[Depends(rate_limit)])
def audit_add(body: AuditIn, u=Depends(rec)):
    if body.action not in ("export_csv", "print_report", "export_pdf"):
        raise HTTPException(400, "Unknown action.")
    with accounts.Conn() as c:
        audit(c, u, body.action, body.target)
    return {"ok": True}


@router.get("/api/hub/dashboard", dependencies=[Depends(rate_limit)])
def dashboard(u=Depends(rec)):
    purge()
    with accounts.Conn() as c:
        camps = c.run("SELECT COUNT(*) AS n, SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS open FROM campaigns WHERE org_id=?", (u["org_id"],))[0]
        a = c.run("SELECT COUNT(*) AS total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done, SUM(CASE WHEN status='started' THEN 1 ELSE 0 END) AS started, AVG(score) AS avg, AVG(CASE WHEN status='done' THEN finished-started END) AS secs FROM attempts WHERE campaign_id IN (SELECT id FROM campaigns WHERE org_id=?)", (u["org_id"],))[0]
        stages = {r["stage"]: r["n"] for r in c.run("SELECT stage, COUNT(*) AS n FROM pipeline WHERE org_id=? GROUP BY stage", (u["org_id"],))}
        per = c.run("SELECT c.name AS name, c.role_title AS role, COUNT(a.id) AS total, SUM(CASE WHEN a.status='done' THEN 1 ELSE 0 END) AS done, AVG(a.score) AS avg FROM campaigns c LEFT JOIN attempts a ON a.campaign_id=c.id WHERE c.org_id=? GROUP BY c.id, c.name, c.role_title, c.created ORDER BY c.created DESC LIMIT 10", (u["org_id"],))
    total, done = a["total"] or 0, a["done"] or 0
    return {"campaigns": camps["n"] or 0, "open": camps["open"] or 0, "invited": total, "completed": done, "in_progress": a["started"] or 0,
            "completion_rate": round(100 * done / total) if total else None, "avg_score": round(a["avg"]) if a["avg"] is not None else None,
            "avg_minutes": round((a["secs"] or 0) / 60, 1) if a["secs"] else None, "pipeline": {s: stages.get(s, 0) for s in STAGES},
            "per_campaign": [{"name": p["name"], "role": p["role"], "total": p["total"] or 0, "done": p["done"] or 0, "avg": round(p["avg"]) if p["avg"] is not None else None} for p in per]}


# ---------------- API export (API key) ----------------
@router.get("/api/v1/results", dependencies=[Depends(rate_limit)])
def api_results(request: Request, campaign: str = "", format: str = "json"):
    key = request.headers.get("x-api-key", "")
    if not key.startswith("mr_"):
        raise HTTPException(401, "Send your API key in the X-API-Key header.")
    h = hashlib.sha256(key.encode()).hexdigest()
    with accounts.Conn() as c:
        o = c.run("SELECT id FROM orgs WHERE api_key_hash=?", (h,))
        if not o:
            raise HTTPException(401, "Invalid API key.")
        org = o[0]["id"]
        q = "SELECT c.id AS campaign_id, c.name AS campaign, a.name, a.phone, a.status, a.score, a.finished, a.data FROM attempts a JOIN campaigns c ON c.id=a.campaign_id WHERE c.org_id=?"
        params = [org]
        if campaign:
            q += " AND c.id=?"
            params.append(campaign)
        rows = c.run(q + " ORDER BY a.created LIMIT 5000", tuple(params))
        c.run("INSERT INTO audit (id, org_id, user_email, action, target, ts) VALUES (?,?,?,?,?,?)", (uuid.uuid4().hex, org, "api-key", "api_export", campaign or "all", _now()))
    out = []
    for r in rows:
        d = json.loads(r["data"] or "{}")
        out.append({"campaign_id": r["campaign_id"], "campaign": r["campaign"], "name": r["name"], "phone": r["phone"], "status": r["status"],
                    "score": None if r["score"] is None else round(r["score"]), "finished": r["finished"], "signals": "; ".join(d.get("signals", []))})
    if format == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(out[0].keys()) if out else ["campaign_id"])
        w.writeheader()
        for r in out:
            w.writerow({k: (("'" + str(v)) if isinstance(v, str) and v[:1] in "=+-@" else v) for k, v in r.items()})
        return Response(buf.getvalue(), media_type="text/csv")
    return {"results": out}


# ---------------- public: screening links ----------------
def _client_plan(plan: dict, camp: dict) -> dict:
    out = {"voice": [{"q": q["q"]} for q in plan.get("voice", [])], "modules": json.loads(camp["modules"]), "secs": camp["secs"]}
    if "typing" in out["modules"]:
        out["typing"] = hubdata.TYPING[plan["typing"] % len(hubdata.TYPING)]
    if "reading" in out["modules"]:
        out["reading"] = hubdata.READING[plan["reading"] % len(hubdata.READING)]
    if "quiz" in out["modules"]:
        out["quiz"] = [{"q": hubdata.QUIZ[i]["q"], "o": hubdata.QUIZ[i]["o"]} for i in plan["quiz"]]
    if "aptitude" in out["modules"]:
        out["aptitude"] = [{"q": it["q"], "o": it["o"]} for it in hubdata.aptitude(plan["apt"])]
    return out


def _load(token: str):
    purge()
    with accounts.Conn() as c:
        if token.startswith("o-"):
            camp = c.run("SELECT * FROM campaigns WHERE id=?", (token[2:],))
            att = None
        else:
            r = c.run("SELECT * FROM attempts WHERE token=?", (token,))
            att = r[0] if r else None
            camp = c.run("SELECT * FROM campaigns WHERE id=?", (att["campaign_id"],)) if att else []
        org = c.run("SELECT name, brand_color, logo FROM orgs WHERE id=?", (camp[0]["org_id"],)) if camp else []
    if not camp:
        raise HTTPException(404, "This link is not valid. Please ask the recruiter for a new one.")
    return camp[0], att, (org[0] if org else {"name": "", "brand_color": "#5b8cff", "logo": ""})


def _check_open(camp):
    if camp["status"] != "open":
        raise HTTPException(410, "This screening has been closed by the recruiter.")
    if camp["expires"] < _now():
        raise HTTPException(410, "This link has expired. Please ask the recruiter for a new one.")


@router.get("/api/s/{token}", dependencies=[Depends(scr_limit)])
def scr_info(token: str):
    camp, att, org = _load(token)
    _check_open(camp)
    info = {"campaign": {"name": camp["name"], "role": camp["role_title"], "modules": json.loads(camp["modules"]), "secs": camp["secs"], "n": camp["n_questions"],
                         "lang": camp["lang"], "retention_days": camp["retention_days"]},
            "brand": {"name": org["name"], "color": org["brand_color"], "logo": org["logo"]}, "open": att is None,
            "status": att["status"] if att else "new", "name": att["name"] if att else ""}
    return info


class StartIn(BaseModel):
    name: str = Field("", max_length=80)
    phone: str = Field("", max_length=30)
    consent: bool = False


def _plan_for(camp, token_seed: str) -> dict:
    mods = json.loads(camp["modules"])
    rnd = int(hashlib.sha256(token_seed.encode()).hexdigest()[:8], 16)
    plan = {"voice": screening.draw_questions(camp["pool"], camp["n_questions"], token_seed) if "voice" in mods else [],
            "typing": rnd % 97, "reading": (rnd // 7) % 97, "apt": rnd}
    import random
    plan["quiz"] = random.Random(rnd).sample(range(len(hubdata.QUIZ)), 10)
    return plan


@router.post("/api/s/{token}/start", dependencies=[Depends(scr_limit)])
def scr_start(token: str, body: StartIn):
    camp, att, org = _load(token)
    _check_open(camp)
    if not body.consent:
        raise HTTPException(400, "Please tick the consent box to continue.")
    with accounts.Conn() as c:
        if att is None:  # open campaign link: one attempt per phone number
            name = body.name.strip()[:80]
            ph = phone_norm(body.phone)
            if not name or len(ph) < 8:
                raise HTTPException(400, "Please enter your name and a valid phone number.")
            ex = c.run("SELECT * FROM attempts WHERE campaign_id=? AND phone=?", (camp["id"], ph))
            if ex:
                att = ex[0]
            else:
                if not camp["open_link"]:
                    raise HTTPException(403, "This screening is by personal invite only.")
                tok = secrets.token_urlsafe(8)
                aid = uuid.uuid4().hex
                c.run("INSERT INTO attempts (id, campaign_id, token, name, phone, status, data, created) VALUES (?,?,?,?,?,?,?,?)", (aid, camp["id"], tok, name, ph, "invited", "{}", _now()))
                att = c.run("SELECT * FROM attempts WHERE id=?", (aid,))[0]
        if att["status"] == "done":
            raise HTTPException(409, "You have already completed this screening. Thank you.")
        d = json.loads(att["data"] or "{}")
        if "plan" not in d:
            d["plan"] = _plan_for(camp, att["token"])
            d["voice"], d["leaves"], d["issued"] = [], 0, {"v0": _now()}
        if body.name.strip() and att["status"] == "invited":
            att["name"] = body.name.strip()[:80]
        c.run("UPDATE attempts SET status='started', started=COALESCE(started, ?), consent_at=COALESCE(consent_at, ?), name=?, data=? WHERE id=?",
              (_now(), _now(), att["name"], json.dumps(d), att["id"]))
    done_voice = len([v for v in d["voice"] if v.get("fu_done")])
    return {"token": att["token"], "plan": _client_plan(d["plan"], camp), "progress": {"voice_done": done_voice, "modules_done": [m for m in ("typing", "reading", "quiz", "apt") if m in d]},
            "pending_followup": next(({"idx": v["idx"], "text": v["fu_text"]} for v in d["voice"] if v.get("fu_text") and not v.get("fu_done")), None)}


def _live(token: str):
    camp, att, org = _load(token)
    if att is None:
        raise HTTPException(400, "Open the link and press Start first.")
    _check_open(camp)
    if att["status"] == "done":
        raise HTTPException(409, "This screening is already completed.")
    if att["status"] != "started":
        raise HTTPException(400, "Please press Start first.")
    return camp, att, json.loads(att["data"] or "{}")


def _save(att, d, **extra):
    with accounts.Conn() as c:
        c.run("UPDATE attempts SET data=? WHERE id=?", (json.dumps(d), att["id"]))


class VoiceIn(BaseModel):
    idx: int = Field(ge=0, le=20)
    text: str = Field("", max_length=3000)
    think: float = Field(0, ge=0, le=600)
    secs: float = Field(0, ge=0, le=600)
    pauses: int = Field(0, ge=0, le=500)
    followup: bool = False
    leaves: int = Field(0, ge=0, le=500)


@router.post("/api/s/{token}/voice", dependencies=[Depends(scr_limit)])
def scr_voice(token: str, body: VoiceIn):
    camp, att, d = _live(token)
    plan = d["plan"]["voice"]
    if body.idx >= len(plan):
        raise HTTPException(400, "Unknown question.")
    d["leaves"] = max(d.get("leaves", 0), body.leaves)
    d.setdefault("issued", {})
    q = plan[body.idx]
    if not body.followup:
        if any(v["idx"] == body.idx for v in d["voice"]):
            raise HTTPException(409, "Already answered.")
        elapsed = _now() - d["issued"].get(f"v{body.idx}", _now())
        wc = len(screening.words(body.text))
        res = screening.score_answer(q["q"], q["ref"], body.text)
        rec_ = {"idx": body.idx, "q": q["q"], "text": body.text.strip(), "score": res["score"], "words": wc, "notes": res["notes"], "think": round(body.think, 1), "secs": round(body.secs, 1),
                "pauses": body.pauses, "late": elapsed > camp["secs"] + 20, "ref_sim": round(screening.sim(body.text, q["ref"]), 2)}
        fu = screening.follow_up(q["q"], body.text, att["token"] + str(body.idx))
        rec_["fu_text"] = fu
        d["voice"].append(rec_)
        d["issued"][f"f{body.idx}"] = _now()
        _save(att, d)
        return {"follow_up": fu}
    rec_ = next((v for v in d["voice"] if v["idx"] == body.idx), None)
    if not rec_ or rec_.get("fu_done"):
        raise HTTPException(409, "No follow-up pending.")
    rec_["fu_answer"] = body.text.strip()
    rec_["fu_ok"] = screening.consistent(rec_["text"], body.text)
    fu_res = screening.score_answer(q["q"], q["ref"], body.text)
    rec_["fu_score"] = fu_res["score"]
    rec_["fu_done"] = True
    d["issued"][f"v{body.idx + 1}"] = _now()
    _save(att, d)
    return {"ok": True}


class ModIn(BaseModel):
    module: str
    typed: str = Field("", max_length=4000)
    said: str = Field("", max_length=4000)
    secs: float = Field(60, ge=0, le=600)
    answers: list[int] = Field(default_factory=list, max_length=40)
    leaves: int = Field(0, ge=0, le=500)


@router.post("/api/s/{token}/module", dependencies=[Depends(scr_limit)])
def scr_module(token: str, body: ModIn):
    camp, att, d = _live(token)
    mods = json.loads(camp["modules"])
    key = {"typing": "typing", "reading": "reading", "quiz": "quiz", "aptitude": "apt"}.get(body.module)
    if not key or body.module not in mods:
        raise HTTPException(400, "Unknown test.")
    d["leaves"] = max(d.get("leaves", 0), body.leaves)
    if key in d:
        return d[key]
    plan = d["plan"]
    if key == "typing":
        res = screening.typing_result(hubdata.TYPING[plan["typing"] % len(hubdata.TYPING)], body.typed, body.secs)
    elif key == "reading":
        res = screening.reading_result(hubdata.READING[plan["reading"] % len(hubdata.READING)], body.said)
    elif key == "quiz":
        res = screening.mcq_result([hubdata.QUIZ[i] for i in plan["quiz"]], body.answers)
    else:
        res = screening.mcq_result(hubdata.aptitude(plan["apt"]), body.answers)
    d[key] = res
    _save(att, d)
    return {"ok": True}


class FinishIn(BaseModel):
    leaves: int = Field(0, ge=0, le=500)


@router.post("/api/s/{token}/finish", dependencies=[Depends(scr_limit)])
def scr_finish(token: str, body: FinishIn):
    camp, att, d = _live(token)
    d["leaves"] = max(d.get("leaves", 0), body.leaves)
    parts = []
    voice = d.get("voice", [])
    if voice:
        sc = [(v["score"] * 0.75 + (v.get("fu_score", v["score"])) * 0.25) for v in voice]
        parts.append(sum(sc) / len(sc))
    for k in ("typing", "reading", "quiz", "apt"):
        if k in d:
            parts.append(d[k]["score"])
    score = sum(parts) / len(parts) if parts else 0
    with accounts.Conn() as c:
        others = c.run("SELECT data FROM attempts WHERE campaign_id=? AND id<>? AND status='done' LIMIT 100", (camp["id"], att["id"]))
        other_texts = [" ".join(v.get("text", "") for v in json.loads(o["data"] or "{}").get("voice", [])) for o in others]
        d["signals"] = screening.integrity(voice, d["leaves"], other_texts)
        c.run("UPDATE attempts SET status='done', finished=?, score=?, delete_after=?, data=? WHERE id=?",
              (_now(), score, _now() + camp["retention_days"] * 86400, json.dumps(d), att["id"]))
    return {"ok": True, "retention_days": camp["retention_days"]}


@router.delete("/api/s/{token}/mine", dependencies=[Depends(scr_limit)])
def scr_delete(token: str):
    camp, att, org = _load(token)
    if att is None:
        raise HTTPException(404, "Nothing to delete.")
    with accounts.Conn() as c:
        c.run("DELETE FROM attempts WHERE id=?", (att["id"],))
    return {"ok": True}


@router.get("/s/{token}")
def scr_page(token: str):
    return FileResponse(os.path.join(STATIC, "screen.html"), media_type="text/html", headers={"Cache-Control": "no-cache", "X-Robots-Tag": "noindex"})


# ---------------- public: skill tests (practice, nothing stored) ----------------
def _practice_items(module: str, seed: int):
    import random
    rnd = random.Random(seed)
    if module == "typing":
        return hubdata.TYPING[seed % len(hubdata.TYPING)]
    if module == "reading":
        return hubdata.READING[seed % len(hubdata.READING)]
    if module == "quiz":
        return [hubdata.QUIZ[i] for i in rnd.sample(range(len(hubdata.QUIZ)), 10)]
    if module == "aptitude":
        return hubdata.aptitude(seed)
    raise HTTPException(404, "Unknown test.")


@router.get("/api/practice/{module}", dependencies=[Depends(scr_limit)])
def practice_get(module: str, seed: int = 0):
    seed = seed or secrets.randbelow(10**6) + 1
    items = _practice_items(module, seed)
    if isinstance(items, str):
        return {"seed": seed, "text": items}
    return {"seed": seed, "items": [{"q": i["q"], "o": i["o"]} for i in items]}


class PracticeIn(BaseModel):
    seed: int = Field(ge=1, le=10**7)
    typed: str = Field("", max_length=4000)
    said: str = Field("", max_length=4000)
    secs: float = Field(60, ge=0, le=600)
    answers: list[int] = Field(default_factory=list, max_length=40)


@router.post("/api/practice/{module}", dependencies=[Depends(scr_limit)])
def practice_post(module: str, body: PracticeIn):
    items = _practice_items(module, body.seed)
    if module == "typing":
        return screening.typing_result(items, body.typed, body.secs)
    if module == "reading":
        return screening.reading_result(items, body.said)
    res = screening.mcq_result(items, body.answers)
    res["correct_answers"] = [i["a"] for i in items]
    return res


# ---------------- public: status and Play Store link file ----------------
@router.get("/api/status")
def status():
    ok = True
    try:
        with accounts.Conn() as c:
            c.run("SELECT 1 AS x")
    except Exception:
        ok = False
    from app import llm
    return {"status": "ok" if ok else "degraded", "database": "ok" if ok else "error", "ai": "available" if not llm.mock_mode() else "not configured",
            "uptime_minutes": round((_now() - STARTED) / 60), "server_time": int(_now())}


@router.get("/help")
def help_page():
    return FileResponse(os.path.join(STATIC, "help.html"), media_type="text/html")


@router.get("/.well-known/assetlinks.json")
def assetlinks():
    """Play Store (TWA) ownership file. Set ASSETLINKS_JSON on the host with the JSON Google gives at publish time."""
    raw = os.environ.get("ASSETLINKS_JSON", "[]")
    try:
        data = json.loads(raw)
    except Exception:
        data = []
    return JSONResponse(data)
