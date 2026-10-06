import threading
import time

from app import bank, brief, llm


def _run_parallel(fn, n=6):
    out, errs = [], []

    def go():
        try:
            out.append(fn())
        except Exception as e:  # pragma: no cover
            errs.append(e)

    ts = [threading.Thread(target=go) for _ in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs
    return out


def test_same_company_bank_makes_one_ai_call(monkeypatch):
    calls = []

    def fake(task, system, user, model=None):
        calls.append(task)
        time.sleep(0.3)
        return {"note": "n", "questions": [{"type": "technical", "level": "easy", "question": "Q?", "hint": "h"}]}

    monkeypatch.setattr(llm, "chat_json", fake)
    bank._cache.clear()
    out = _run_parallel(lambda: bank.company_questions("SingleFlightCo", "QA", "US"))
    assert len(out) == 6 and len(calls) == 1


def test_same_company_brief_makes_one_ai_call(monkeypatch):
    calls = []

    def fake(task, system, user, model=None):
        calls.append(task)
        time.sleep(0.3)
        return {"summary": "s"}

    monkeypatch.setattr(llm, "chat_json", fake)
    brief._cache.clear()
    out = _run_parallel(lambda: brief.build("SingleFlightCo2", "QA", "US"))
    assert len(out) == 6 and len(calls) == 1


def test_different_keys_do_not_block_each_other(monkeypatch):
    from app import singleflight

    with singleflight.lock(("x", 1)):
        done = []

        def other():
            with singleflight.lock(("x", 2)):
                done.append(1)

        t = threading.Thread(target=other)
        t.start()
        t.join(1)
        assert done == [1]
