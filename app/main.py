import io
import os

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import llm, services
from app.guard import rate_limit

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


@app.exception_handler(llm.LLMError)
async def llm_error(_: Request, exc: llm.LLMError):
    return JSONResponse({"detail": "The AI service is busy or unavailable. Please try again in a moment."}, status_code=502)


class StartIn(BaseModel):
    resume: str = Field(max_length=60000)
    role: str = Field(max_length=200)
    jd: str = Field("", max_length=30000)
    country: str = "US"


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
    return services.start_session(_need_resume(body.resume), _need_role(body.role), body.jd, body.country)


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


@app.get("/sw.js")
def service_worker():
    # Served from the root so its scope covers the whole app.
    return FileResponse(os.path.join(STATIC, "sw.js"), media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
