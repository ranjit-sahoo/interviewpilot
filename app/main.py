from fastapi import FastAPI

app = FastAPI(title="InterviewPilot")


@app.get("/health")
def health():
    return {"status": "ok"}
