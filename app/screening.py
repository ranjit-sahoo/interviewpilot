"""Rule-based scoring for screening campaigns. No AI. Scores are assistive signals, not hiring decisions.
Voice answers arrive as text from the browser's speech recognition, so nothing here judges audio, accent or pronunciation."""
import difflib
import random
import re

from app import hubdata
from app.basic_in_data import DATA

STOP = set("""a an the and or but if so to of in on at for with from by is am are was were be been being i me my we our you your he she it they them this that these those
as do does did have has had not no yes can could would should will shall may might just very really also about into than then there here what when where why how which who whom
will able like get got make made let us its it's""".split())
STRUCT = ("because", "for example", "for instance", "so that", "as a result", "therefore", "first", "then", "finally", "i learned", "result", "because of")
FILLER = re.compile(r"\b(um+|uh+|erm|you know|i mean|basically|actually)\b", re.I)


def words(t: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", (t or "").lower())


def content(t: str) -> set:
    return {w for w in words(t) if len(w) > 3 and w not in STOP}


def pool_for(pool: str) -> list[dict]:
    return [o for o in _pool_raw(pool) if o["q"].rstrip().endswith(("?", "."))]  # drop cut-off or non-question entries


def _pool_raw(pool: str) -> list[dict]:
    if pool in hubdata.EXTRA_ROLES:
        gen = [o for o in DATA if o["cat"] == "general" and o["iv"] and o["ref"] and o["id"] != "A1"]
        extra = [{"id": f"{pool}{i}", "q": q, "ref": k} for i, (q, k) in enumerate(hubdata.EXTRA_ROLES[pool][1])]
        return extra + gen[:12]
    role = [o for o in DATA if o["cat"] == pool and o["iv"] and (o["ref"] or o["tip"])]
    gen = [o for o in DATA if o["cat"] == "general" and o["iv"] and o["ref"] and o["id"] != "A1"]
    return role + gen[:12]


def draw_questions(pool: str, n: int, seed: str) -> list[dict]:
    """First question is always the self-introduction; the rest are a random draw, different for every candidate."""
    rng = random.Random(seed)
    items = pool_for(pool if (pool in hubdata.POOL_LABELS) else "bpo")
    rng.shuffle(items)
    out = [{"id": "A1", "q": "Tell me about yourself.", "ref": "name from completed graduation studies skill learn quickly career job company grow"}]
    for o in items:
        if len(out) >= n:
            break
        out.append({"id": o["id"], "q": o["q"], "ref": o["ref"] or o["tip"]})
    return out[:n]


def score_answer(question: str, ref: str, text: str) -> dict:
    ws = words(text)
    n = len(ws)
    if n < 3:
        return {"score": 0, "words": n, "notes": ["No usable answer captured"]}
    kw = content(ref) or content(question)
    cov = len(kw & content(text)) / max(1, min(len(kw), 8))
    rel = len(content(question) & content(text)) / max(1, len(content(question)))
    cover = min(1.0, 0.7 * min(cov, 1) + 0.3 * min(rel * 2, 1))
    length = 1.0 if 25 <= n <= 140 else (n / 25 if n < 25 else max(0.4, 140 / n))
    low = " ".join(ws)
    struct = min(1.0, sum(1 for s in STRUCT if s in low) / 2)
    sents = max(1, len(re.findall(r"[.!?]", text)) or 1)
    avg = n / sents
    clarity = 1.0 if avg <= 28 else max(0.4, 28 / avg)
    fill = len(FILLER.findall(text)) / max(1, n)
    clarity *= max(0.5, 1 - fill * 4)
    uniq = len(set(ws)) / n
    if uniq < 0.4 and n > 15:
        clarity *= 0.6
    score = round(100 * (0.40 * cover + 0.25 * length + 0.15 * struct + 0.20 * clarity))
    notes = []
    if n < 20:
        notes.append("Very short answer")
    if cover < 0.3:
        notes.append("Few points related to the question")
    if fill > 0.05:
        notes.append("Many filler words")
    if n > 160:
        notes.append("Very long answer")
    return {"score": score, "words": n, "notes": notes}


_FU = [
    "You mentioned \"{kw}\". Can you give one real example from your own life or work?",
    "Tell me more about \"{kw}\". What exactly did you do?",
    "Why is \"{kw}\" important for this job?",
]
_FU_SHORT = "Can you say a little more? Please give one clear example."


def follow_up(question: str, text: str, seed: str) -> str:
    """Rule-based probe that refers to something the candidate just said. Scripts tend to break here."""
    ws = words(text)
    if len(ws) < 15:
        return _FU_SHORT
    cands = [w for w in ws if len(w) > 5 and w not in STOP and w not in content(question)]
    if not cands:
        return _FU_SHORT
    freq = {}
    for w in cands:
        freq[w] = freq.get(w, 0) + 1
    kw = sorted(freq, key=lambda w: (-freq[w], -len(w)))[0]
    return random.Random(seed).choice(_FU).format(kw=kw)


def consistent(first: str, second: str) -> bool:
    a, b = content(first), content(second)
    return bool(a & b) or len(words(second)) < 4


def sim(a: str, b: str) -> float:
    sa = {" ".join(w[i:i + 3]) for w in [words(a)] for i in range(max(0, len(w) - 2))}
    sb = {" ".join(w[i:i + 3]) for w in [words(b)] for i in range(max(0, len(w) - 2))}
    return len(sa & sb) / max(1, len(sa | sb)) if sa and sb else 0.0


def typing_result(passage: str, typed: str, secs: float) -> dict:
    secs = max(5.0, min(float(secs or 60), 300.0))
    a, b = passage.split(), (typed or "").split()
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    right = sum(t.size for t in m.get_matching_blocks())
    acc = right / max(1, len(a))
    wpm = right / (secs / 60)
    return {"wpm": round(wpm), "accuracy": round(100 * acc), "score": round(min(100, 100 * acc * min(1, wpm / 35)))}


def reading_result(passage: str, said: str) -> dict:
    a, b = words(passage), words(said)
    if not b:
        return {"match": 0, "score": 0}
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    right = sum(t.size for t in m.get_matching_blocks())
    pct = round(100 * right / max(1, len(a)))
    return {"match": pct, "score": pct}


def mcq_result(items: list[dict], answers: list) -> dict:
    ok = 0
    for i, it in enumerate(items):
        if i < len(answers) and answers[i] == it["a"]:
            ok += 1
    return {"correct": ok, "total": len(items), "score": round(100 * ok / max(1, len(items)))}


def integrity(voice: list[dict], leaves: int, other_texts: list[str]) -> list[str]:
    """Soft signals to ask about in a live call. Never proof of cheating."""
    flags = []
    if leaves >= 3:
        flags.append(f"Left the page {leaves} times")
    elif leaves:
        flags.append(f"Left the page {leaves} time(s)")
    late = [v for v in voice if v.get("late")]
    if late:
        flags.append(f"{len(late)} answer(s) sent after the time limit")
    smooth = [v for v in voice if v.get("words", 0) >= 60 and v.get("pauses", 9) == 0]
    if smooth:
        flags.append(f"{len(smooth)} long answer(s) with no pauses at all (could be read from a script)")
    delayed = [v for v in voice if v.get("think", 0) >= 15 and v.get("words", 0) >= 50]
    if delayed:
        flags.append(f"{len(delayed)} answer(s) started after a long silence, then ran fluently")
    ref_close = [v for v in voice if v.get("ref_sim", 0) >= 0.5]
    if ref_close:
        flags.append(f"{len(ref_close)} answer(s) very close to a model answer's wording")
    bad_fu = [v for v in voice if v.get("fu_ok") is False]
    if bad_fu:
        flags.append(f"{len(bad_fu)} follow-up answer(s) did not relate to the first answer")
    full = " ".join(v.get("text", "") for v in voice)
    for o in other_texts:
        if sim(full, o) >= 0.5 and len(words(full)) > 40:
            flags.append("Wording very similar to another candidate in this campaign")
            break
    return flags
