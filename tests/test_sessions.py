import os
import tempfile

os.environ.pop("DATABASE_URL", None)
os.environ["INTERVIEWPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "s.sqlite3")

from app import accounts, db

accounts.SQLITE_PATH = os.environ["INTERVIEWPILOT_DB"]


def test_session_survives_process_restart_and_prunes_old():
    sid = db.create({"role": "QA", "turns": [1, 2]})
    db._ready = False  # simulate a fresh process: nothing cached in memory
    assert db.load(sid) == {"role": "QA", "turns": [1, 2]}
    db.save(sid, {"role": "QA", "turns": [1, 2, 3]})
    db._ready = False
    assert db.load(sid)["turns"] == [1, 2, 3]
    assert db.load("nope") is None
    with accounts.Conn() as c:
        c.run("INSERT INTO sessions (id, data, created) VALUES (?, ?, ?)", ("old1", "{}", 1.0))
    db._last_prune = 0.0
    db.create({"x": 1})
    assert db.load("old1") is None
