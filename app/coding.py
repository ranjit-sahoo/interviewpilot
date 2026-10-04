"""Coding practice: curated problems, AI evaluation of the submitted solution, and hints.

Text mode: the candidate writes code in the browser editor and Nemotron reviews it
(correctness, edge cases, complexity, style). Code is never executed on the server.
"""
from app import llm

LANGS = ["Python", "JavaScript", "Java", "SQL"]

# id, title, level, topic, statement, per-language starter handled generically
PROBLEMS = [
    ("two-sum", "Two Sum", "easy", "arrays, hash map",
     "Given a list of integers and a target, return the indices of the two numbers that add up to the target. Exactly one solution exists. Aim for O(n)."),
    ("valid-parens", "Valid Parentheses", "easy", "stack, strings",
     "Given a string containing only ()[]{} characters, return true if the brackets are balanced and correctly nested."),
    ("reverse-words", "Reverse Words in a String", "easy", "strings",
     "Reverse the order of words in a sentence. Collapse repeated spaces and trim the ends. Do not use a built-in that does the whole job."),
    ("anagram-groups", "Group Anagrams", "medium", "hash map, strings",
     "Given a list of words, group the words that are anagrams of each other. Return a list of groups."),
    ("longest-substring", "Longest Substring Without Repeating Characters", "medium", "sliding window",
     "Return the length of the longest substring of a string that has no repeating characters. Aim for O(n)."),
    ("merge-intervals", "Merge Intervals", "medium", "sorting, arrays",
     "Given a list of [start, end] intervals, merge all overlapping intervals and return the result sorted by start."),
    ("lru-cache", "LRU Cache", "medium", "design, hash map, linked list",
     "Design a cache with a fixed capacity supporting get(key) and put(key, value) in O(1). When full, evict the least recently used key."),
    ("top-k-frequent", "Top K Frequent Elements", "medium", "heap, hash map",
     "Given a list of integers and k, return the k most frequent elements. Better than O(n log n) is a plus."),
    ("binary-search-rotated", "Search in Rotated Sorted Array", "hard", "binary search",
     "A sorted array of distinct integers was rotated at an unknown pivot. Find the index of a target in O(log n), or -1."),
    ("sql-second-highest", "SQL: Second Highest Salary", "easy", "sql",
     "Table Employee(id, name, salary, department_id). Write a query that returns the second highest distinct salary, or NULL if it does not exist."),
    ("sql-dept-top-earners", "SQL: Top 3 Earners per Department", "medium", "sql, window functions",
     "Tables Employee(id, name, salary, department_id) and Department(id, name). Return department name, employee name and salary for the top 3 distinct salaries in each department."),
    ("sql-duplicate-emails", "SQL: Duplicate Emails", "easy", "sql",
     "Table Person(id, email). Return every email that appears more than once."),
    ("rate-limiter", "Design: Rate Limiter", "hard", "design, sliding window",
     "Implement a rate limiter that allows at most N requests per user in any rolling 60 second window. Explain how it behaves under concurrent calls."),
    ("flatten-json", "Flatten Nested JSON", "medium", "recursion, objects",
     "Flatten a nested dict/object into one level with dot-separated keys, e.g. {a:{b:1}} becomes {'a.b':1}. Handle arrays by index."),
]
_BY_ID = {p[0]: p for p in PROBLEMS}

STARTERS = {
    "Python": "def solve(*args):\n    # write your solution\n    pass\n",
    "JavaScript": "function solve(...args) {\n  // write your solution\n}\n",
    "Java": "class Solution {\n    // write your solution\n}\n",
    "SQL": "-- write your query\nSELECT 1;\n",
}


def listing() -> list[dict]:
    return [{"id": i, "title": t, "level": lv, "topic": tp} for i, t, lv, tp, _ in PROBLEMS]


def get(pid: str) -> dict:
    p = _BY_ID.get(pid)
    if not p:
        raise KeyError(pid)
    i, t, lv, tp, st = p
    langs = ["SQL"] if i.startswith("sql-") else [l for l in LANGS if l != "SQL"]
    return {"id": i, "title": t, "level": lv, "topic": tp, "statement": st, "languages": langs,
            "starters": {l: STARTERS[l] for l in langs}}


EVAL_SYSTEM = """You are a strict but encouraging senior engineer reviewing a candidate's interview solution.
You cannot run code, so reason carefully by reading it and tracing it on the sample and edge cases.
Do not give the full corrected solution unless the answer is already correct. Return ONLY JSON:
{"verdict": "correct|partially_correct|incorrect",
 "score": 1-10 int,
 "summary": str (2 sentences, specific),
 "bugs": [str] (concrete bugs or missed edge cases, each with an input that breaks it; empty if none),
 "complexity": {"time": str, "space": str, "optimal": bool, "note": str},
 "style": [str] (up to 3 readability or idiom points),
 "next_step": str (one concrete thing to do next, a nudge not a solution),
 "better_approach": str (describe the optimal approach in words; empty if already optimal)}"""

HINT_SYSTEM = """You are an interviewer giving a hint on a coding problem. Give ONE short hint that nudges toward the
approach without giving the solution or code. Hint level {level} of 3 (1 = vague direction, 3 = nearly the idea).
Return ONLY JSON: {{"hint": str}}"""

MAX_CODE = 12000


def _check(pid: str, language: str, code: str):
    prob = get(pid)  # KeyError -> 404
    if language not in prob["languages"]:
        raise ValueError("Pick one of: " + ", ".join(prob["languages"]))
    code = (code or "").strip()
    if len(code) < 5:
        raise ValueError("Write some code first.")
    if len(code) > MAX_CODE:
        raise ValueError("Code is too long (12,000 characters max).")
    return prob, code


def evaluate(pid: str, language: str, code: str) -> dict:
    prob, code = _check(pid, language, code)
    user = f"PROBLEM: {prob['title']} ({prob['level']})\n{prob['statement']}\n\nLANGUAGE: {language}\n\nSOLUTION:\n{code}"
    out = llm.chat_json("code_eval", EVAL_SYSTEM, user, model=llm.FAST_MODEL)
    cx = out.get("complexity") if isinstance(out.get("complexity"), dict) else {}
    verdict = out.get("verdict") if out.get("verdict") in ("correct", "partially_correct", "incorrect") else "partially_correct"
    try:
        score = max(1, min(10, int(out.get("score", 5))))
    except (TypeError, ValueError):
        score = 5
    lst = lambda v, n: [str(x)[:400] for x in v][:n] if isinstance(v, list) else []
    return {
        "verdict": verdict, "score": score,
        "summary": str(out.get("summary", ""))[:600],
        "bugs": lst(out.get("bugs"), 6),
        "complexity": {"time": str(cx.get("time", ""))[:80], "space": str(cx.get("space", ""))[:80],
                       "optimal": bool(cx.get("optimal", False)), "note": str(cx.get("note", ""))[:300]},
        "style": lst(out.get("style"), 3),
        "next_step": str(out.get("next_step", ""))[:400],
        "better_approach": str(out.get("better_approach", ""))[:600],
    }


def hint(pid: str, level: int, code: str = "") -> dict:
    prob = get(pid)
    level = max(1, min(3, int(level)))
    user = f"PROBLEM: {prob['title']}\n{prob['statement']}\n\nCANDIDATE CODE SO FAR:\n{(code or '')[:3000] or '(none)'}"
    out = llm.chat_json("code_hint", HINT_SYSTEM.format(level=level), user, model=llm.FAST_MODEL)
    return {"level": level, "hint": str(out.get("hint", ""))[:500]}
