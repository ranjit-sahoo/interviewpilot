# InterviewPilot

AI interview prep agent for US IT job candidates. Built for the Nebius x NVIDIA Global AI Hackathon (track: Best Apps and Agents).

## What it does
1. **Resume review** - upload your resume and target role. Get a list of weaknesses and concrete advice on how to fix each one.
2. **Tailored questions** - technical, behavioral and US-client scenario questions built from your resume and the role (optional job description).
3. **Realistic mock interview** - one question at a time, with follow-ups, like a real interviewer.
4. **Per-answer feedback** - 1-5 scores for clarity, depth, correctness and STAR structure, plus a stronger sample answer and US-interview tips.
5. **Session report** - overall score, strengths, gaps and a 7-day practice plan.

## Stack
Python FastAPI, SQLite, simple web front end. Models run on **Nebius Token Factory** (OpenAI-compatible API) using **NVIDIA Nemotron**: a larger Nemotron for scoring and reports, a faster one for question generation and follow-ups.

## Run
```
pip install -r requirements.txt
export NEBIUS_API_KEY=...
uvicorn app.main:app --reload
```

Without `NEBIUS_API_KEY` the app runs in demo mode with canned sample replies (offline). With a key it calls Token Factory.
Override models with `FAST_MODEL` and `STRONG_MODEL` (IDs from the Token Factory catalog).

## API
- `POST /api/resume/review` (form: role, resume text or PDF/TXT file, optional jd) - weaknesses and fixes
- `POST /api/session` - start a mock interview, returns first question
- `POST /api/session/{id}/answer` - scores + stronger answer + tips + next question
- `GET /api/session/{id}/report` - overall score, strengths, gaps, 7-day plan

## Tests
`pip install pytest httpx && pytest`

## License
MIT
