import io
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import llm, services

app = FastAPI(title="InterviewPilot")
STATIC = os.path.join(os.path.dirname(__file__), "static")


class StartIn(BaseModel):
    resume: str
    role: str
    jd: str = ""


class AnswerIn(BaseModel):
    answer: str


def _resume_text(resume: str, file: UploadFile | None) -> str:
    if file is not None and file.filename:
        raw = file.file.read()
        if file.filename.lower().endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        return raw.decode("utf-8", errors="ignore")
    return resume


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": llm.mock_mode()}


@app.post("/api/resume/review")
def resume_review(
    role: str = Form(...),
    resume: str = Form(""),
    jd: str = Form(""),
    file: UploadFile | None = File(None),
):
    text = _resume_text(resume, file).strip()
    if len(text) < 30:
        raise HTTPException(400, "Paste your resume text or upload a PDF/TXT file.")
    return services.review_resume(text, role, jd)


@app.post("/api/session")
def start(body: StartIn):
    if len(body.resume.strip()) < 30:
        raise HTTPException(400, "Resume text is too short.")
    return services.start_session(body.resume, body.role, body.jd)


@app.post("/api/session/{sid}/answer")
def answer(sid: str, body: AnswerIn):
    if not body.answer.strip():
        raise HTTPException(400, "Answer is empty.")
    try:
        return services.answer(sid, body.answer)
    except KeyError:
        raise HTTPException(404, "Unknown session")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/session/{sid}/report")
def report(sid: str):
    try:
        return services.report(sid)
    except KeyError:
        raise HTTPException(404, "Unknown session")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
