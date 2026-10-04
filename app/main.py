import io
import os

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import accounts, bank, brief, builder, card, coding, companies, llm, prep, services, star
from app.guard import RateLimiter, client_key, rate_limit

app = FastAPI(title="InterviewPilot")

# A future mobile shell or separate web front end can call the API cross-origin.
# Set CORS_ORIGINS="https://app.example.com,capacitor://localhost" to enable; off by default.
_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _origins:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"], allow_headers=["*"])
STATIC = os.path.join(os.path.dirname(__file__), "static")
MAX_UPLOAD = 5 * 1024 * 1024
LIMITED = [Depends(rate_limit)]
_auth_limiter = RateLimiter(limit=int(os.environ.get("AUTH_RATE_PER_MIN", "10")), window=60.0)
COOKIE = "ip_session"


def auth_limit(request: Request):
    if not _auth_limiter.check(client_key(request)):
        raise HTTPException(429, "Too many attempts. Please wait a minute and try again.")


def current_user(request: Request):
    return accounts.user_for(request.cookies.get(COOKIE))


def need_user(request: Request):
    u = current_user(request)
    if not u:
        raise HTTPException(401, "Please log in to use saved history.")
    return u


def _set_cookie(resp, request: Request, token: str):
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie(COOKIE, token, max_age=accounts.SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=secure, path="/")


@app.exception_handler(llm.LLMError)
async def llm_error(_: Request, exc: llm.LLMError):
    return JSONResponse({"detail": "The AI service is busy or unavailable. Please try again in a moment."}, status_code=502)


class StartIn(BaseModel):
    resume: str = Field(max_length=60000)
    role: str = Field(max_length=200)
    jd: str = Field("", max_length=30000)
    country: str = "US"
    level: str = Field("auto", max_length=20)
    followups: bool = True


class AnswerIn(BaseModel):
    answer: str = Field(max_length=8000)


class DetectIn(BaseModel):
    resume: str = Field(max_length=60000)
    jd: str = Field("", max_length=30000)


class MatchIn(StartIn):
    pass


class NegoStartIn(BaseModel):
    resume: str = Field(max_length=60000)
    role: str = Field(max_length=200)
    country: str = "US"
    current: str = Field("", max_length=200)


class SayIn(BaseModel):
    message: str = Field(max_length=3000)


class Candidate(BaseModel):
    name: str = Field("", max_length=80)
    resume: str = Field(max_length=60000)


class ScreenIn(BaseModel):
    role: str = Field(max_length=200)
    jd: str = Field("", max_length=30000)
    country: str = "US"
    candidates: list[Candidate] = Field(max_length=services.MAX_CANDIDATES)


def _read_upload(file: UploadFile) -> str:
    raw = file.file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "File is too large (5 MB max).")
    if file.filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            raise HTTPException(400, "Could not read this PDF. Try a text-based PDF or paste the text.")
    return raw.decode("utf-8", errors="ignore")


def _need_resume(text: str) -> str:
    text = (text or "").strip()
    if len(text) < 30:
        raise HTTPException(400, "Paste your resume text or upload a PDF/TXT file.")
    return text


def _need_role(role: str) -> str:
    role = (role or "").strip()
    if not role:
        raise HTTPException(400, "Enter the target role.")
    return role


def _guard(fn, *a):
    try:
        return fn(*a)
    except KeyError:
        raise HTTPException(404, "Unknown session")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": llm.mock_mode()}


@app.post("/api/extract", dependencies=LIMITED)
def extract(file: UploadFile = File(...)):
    """Turn an uploaded PDF/TXT into text so the UI can reuse it everywhere."""
    text = _read_upload(file).strip()
    if len(text) < 30:
        raise HTTPException(400, "No readable text found in this file.")
    return {"text": text}


@app.post("/api/detect-country", dependencies=LIMITED)
def detect(body: DetectIn):
    if len(body.resume.strip()) < 30:
        raise HTTPException(400, "Resume text is too short.")
    return services.detect_country(body.resume, body.jd)


@app.post("/api/resume/review", dependencies=LIMITED)
def resume_review(
    role: str = Form(...),
    resume: str = Form(""),
    jd: str = Form(""),
    country: str = Form("US"),
    file: UploadFile | None = File(None),
):
    text = _read_upload(file) if file is not None and file.filename else resume
    return services.review_resume(_need_resume(text), _need_role(role), jd, country)


@app.post("/api/match", dependencies=LIMITED)
def match(body: MatchIn):
    if len(body.jd.strip()) < 30:
        raise HTTPException(400, "Paste the job description to compare against.")
    return services.match_jd(_need_resume(body.resume), _need_role(body.role), body.jd, body.country)


@app.post("/api/session", dependencies=LIMITED)
def start(body: StartIn):
    return services.start_session(_need_resume(body.resume), _need_role(body.role), body.jd, body.country, body.level, body.followups)


@app.post("/api/session/{sid}/answer", dependencies=LIMITED)
def answer(sid: str, body: AnswerIn):
    if not body.answer.strip():
        raise HTTPException(400, "Answer is empty.")
    return _guard(services.answer, sid, body.answer)


@app.get("/api/session/{sid}/report", dependencies=LIMITED)
def report(sid: str):
    return _guard(services.report, sid)


@app.post("/api/negotiation", dependencies=LIMITED)
def nego_start(body: NegoStartIn):
    return services.start_negotiation(_need_resume(body.resume), _need_role(body.role), body.country, body.current)


@app.post("/api/negotiation/{sid}/say", dependencies=LIMITED)
def nego_say(sid: str, body: SayIn):
    if not body.message.strip():
        raise HTTPException(400, "Message is empty.")
    return _guard(services.negotiate, sid, body.message)


@app.get("/api/negotiation/{sid}/report", dependencies=LIMITED)
def nego_report(sid: str):
    return _guard(services.negotiation_report, sid)


@app.post("/api/recruiter/screen", dependencies=LIMITED)
def screen(body: ScreenIn):
    return _guard(
        services.screen_candidates, [c.model_dump() for c in body.candidates], _need_role(body.role), body.jd, body.country
    )


class BankIn(BaseModel):
    role: str = Field("", max_length=200)
    company: str = Field("", max_length=80)
    country: str = "US"
    ai: bool = False


@app.get("/api/bank/roles")
def bank_roles():
    return {"roles": bank.roles()}


@app.post("/api/bank", dependencies=LIMITED)
def question_bank(body: BankIn):
    """Curated role questions (instant) plus optional AI company-specific questions."""
    if not body.role.strip() and not body.company.strip():
        raise HTTPException(400, "Enter a role or a company.")
    out = bank.curated(body.role)
    out["company"] = None
    out["profile"] = companies.find(body.company, body.country)
    if body.company.strip() and (out["profile"] is None or body.ai):
        try:
            out["company"] = bank.company_questions(body.company, body.role, body.country)
        except llm.LLMError:
            out["company_error"] = "Company-specific questions are unavailable right now. Showing the role bank."
    return out


class CodeIn(BaseModel):
    language: str = Field(max_length=20)
    code: str = Field(max_length=coding.MAX_CODE + 1000)


class HintIn(BaseModel):
    level: int = 1
    code: str = Field("", max_length=coding.MAX_CODE)


@app.get("/api/coding/problems")
def coding_list():
    return {"problems": coding.listing()}


@app.get("/api/coding/problems/{pid}")
def coding_get(pid: str):
    return _guard(coding.get, pid)


@app.post("/api/coding/problems/{pid}/evaluate", dependencies=LIMITED)
def coding_eval(pid: str, body: CodeIn):
    return _guard(coding.evaluate, pid, body.language, body.code)


@app.post("/api/coding/problems/{pid}/hint", dependencies=LIMITED)
def coding_hint(pid: str, body: HintIn):
    return _guard(coding.hint, pid, body.level, body.code)


class PolishIn(BaseModel):
    role: str = Field("", max_length=200)
    bullets: list[str] = Field(max_length=builder.MAX_BULLETS)
    country: str = "US"


class SummaryIn(BaseModel):
    role: str = Field("", max_length=200)
    facts: str = Field(max_length=6000)
    country: str = "US"


@app.post("/api/builder/parse", dependencies=LIMITED)
def builder_parse(body: DetectIn):
    return builder.parse(_need_resume(body.resume))


@app.post("/api/builder/polish", dependencies=LIMITED)
def builder_polish(body: PolishIn):
    return {"bullets": _guard(builder.polish, body.role, body.bullets, body.country)}


@app.post("/api/builder/summary", dependencies=LIMITED)
def builder_summary(body: SummaryIn):
    return {"summary": _guard(builder.summary, body.role, body.facts, body.country)}


@app.post("/api/prep", dependencies=LIMITED)
def prep_pack(body: StartIn):
    """The hero flow: tailored questions with model answers (and coding questions) from resume + JD."""
    return prep.build(_need_resume(body.resume), _need_role(body.role), body.jd, body.country)


@app.post("/api/prep/coding", dependencies=LIMITED)
def prep_coding(body: StartIn):
    """Coding questions for technical profiles, loaded separately so the core pack shows up sooner."""
    return prep.build_coding(_need_resume(body.resume), _need_role(body.role), body.jd, body.country)


class StarIn(BaseModel):
    experience: str = Field(max_length=6000)
    question: str = Field("", max_length=400)
    role: str = Field("", max_length=200)
    country: str = "US"


class BriefIn(BaseModel):
    company: str = Field(max_length=80)
    role: str = Field("", max_length=200)
    country: str = "US"


class CardIn(BaseModel):
    name: str = Field("", max_length=40)


@app.post("/api/star", dependencies=LIMITED)
def star_build(body: StarIn):
    if len(body.experience.strip()) < 30:
        raise HTTPException(400, "Describe your experience in a few sentences (30+ characters).")
    return star.build(body.experience, body.question, body.role, body.country)


@app.post("/api/company-brief", dependencies=LIMITED)
def company_brief(body: BriefIn):
    if len(body.company.strip()) < 2:
        raise HTTPException(400, "Enter a company name.")
    return brief.build(body.company, body.role, body.country)


def _base(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


@app.post("/api/session/{sid}/card", dependencies=LIMITED)
def make_card(sid: str, body: CardIn, request: Request):
    s = _guard(services.load_interview, sid)
    rep = _guard(services.report, sid)
    p = card.make_payload(rep, s["turns"], s["role"], s.get("level", "auto"), s["country"], body.name)
    tok = card.sign(p)
    base = _base(request)
    return {"url": f"{base}/c/{tok}", "image": f"{base}/c/{tok}.png", "score": p["s"], "verdict": card.verdict(p["s"])}


@app.get("/c/{token}.png")
def card_png(token: str):
    p = card.verify(token)
    if not p:
        raise HTTPException(404, "Card not found.")
    return Response(card.render_png(p), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/c/{token}")
def card_page(token: str, request: Request):
    p = card.verify(token)
    if not p:
        raise HTTPException(404, "Card not found.")
    return HTMLResponse(card.page(p, token, _base(request)), headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/companies")
def company_list():
    return {"companies": companies.names()}


class AuthIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=200)


class SaveIn(BaseModel):
    kind: str = Field(max_length=30)
    title: str = Field("", max_length=200)
    data: dict | list


@app.post("/api/auth/register", dependencies=[Depends(auth_limit)])
def auth_register(body: AuthIn, request: Request):
    try:
        user, token = accounts.register(body.email, body.password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = JSONResponse({"user": {"email": user["email"]}})
    _set_cookie(resp, request, token)
    return resp


@app.post("/api/auth/login", dependencies=[Depends(auth_limit)])
def auth_login(body: AuthIn, request: Request):
    try:
        user, token = accounts.login(body.email, body.password)
    except PermissionError as e:
        raise HTTPException(401, str(e))
    resp = JSONResponse({"user": {"email": user["email"]}})
    _set_cookie(resp, request, token)
    return resp


@app.post("/api/auth/logout")
def auth_logout(request: Request):
    accounts.logout(request.cookies.get(COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


@app.get("/api/auth/me")
def auth_me(request: Request):
    u = current_user(request)
    return {"user": {"email": u["email"]} if u else None, "persistent": accounts.using_postgres()}


@app.delete("/api/auth/account")
def auth_delete(request: Request, u=Depends(need_user)):
    accounts.delete_account(u["id"])
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


@app.get("/api/history")
def history_list(u=Depends(need_user)):
    return {"items": accounts.list_items(u["id"])}


@app.post("/api/history", dependencies=LIMITED)
def history_save(body: SaveIn, u=Depends(need_user)):
    return _guard(accounts.save_item, u["id"], body.kind, body.title, body.data)


@app.get("/api/history/{iid}")
def history_get(iid: str, u=Depends(need_user)):
    item = accounts.get_item(u["id"], iid)
    if not item:
        raise HTTPException(404, "Not found")
    return item


@app.delete("/api/history/{iid}")
def history_delete(iid: str, u=Depends(need_user)):
    if not accounts.delete_item(u["id"], iid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@app.get("/sw.js")
def service_worker():
    # Served from the root so its scope covers the whole app.
    return FileResponse(os.path.join(STATIC, "sw.js"), media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/_dbg_ip")
def _dbg_ip(request: Request):
    return {"xff": request.headers.get("x-forwarded-for"), "host": request.client.host if request.client else None, "xri": request.headers.get("x-real-ip"), "cf": request.headers.get("cf-connecting-ip")}
