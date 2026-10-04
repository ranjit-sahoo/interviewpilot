"""Deterministic spoken-English metrics (no model call), merged into per-answer feedback."""
import re

FILLERS = ["um", "uh", "erm", "you know", "i mean", "basically", "actually", "like", "sort of", "kind of", "so yeah", "right"]


def analyze(text: str) -> dict:
    words = re.findall(r"[A-Za-z']+", text.lower())
    n = len(words)
    low = " " + " ".join(words) + " "
    found = {}
    for f in FILLERS:
        k = len(re.findall(rf"(?<![a-z']) {re.escape(f)} (?![a-z'])", low)) if " " in f else words.count(f)
        if f == "like":
            k = words.count("like")
        if k:
            found[f] = k
    total = sum(found.values())
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    avg = round(n / len(sentences), 1) if sentences else 0
    return {
        "word_count": n,
        "filler_total": total,
        "filler_rate_pct": round(100 * total / n, 1) if n else 0,
        "fillers": found,
        "avg_sentence_words": avg,
        "too_short": n < 25,
        "too_long_sentences": avg > 30,
    }
