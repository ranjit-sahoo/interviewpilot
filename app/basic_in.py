"""India basic-level interview set (10th/12th/any graduate). His question set is the guaranteed core;
drafted questions cover hotel, cabin crew and airport roles. India only: the US and Other flows never touch this."""
import random
import re

from app.basic_in_data import DATA

ROLE_NAMES = {
    "bpo": "BPO / Call Centre",
    "cabin": "Cabin Crew / Air Hostess",
    "hotel": "Hotel & Hospitality",
    "airport": "Airport Ground Staff",
    "dataentry": "Data Entry / Back Office",
}
ALIASES = {
    "BPO / Call Centre": ["bpo", "call cent", "customer support", "customer service", "customer care", "voice process", "customer associate", "chat support"],
    "Cabin Crew / Air Hostess": ["air hostess", "airhostess", "cabin crew", "flight attendant", "steward", "in-flight", "inflight"],
    "Hotel & Hospitality": ["hotel", "hospitality", "front desk", "housekeeping", "receptionist", "front office", "food and beverage", "f&b", "resort", "waiter", "guest relation"],
    "Airport Ground Staff": ["airport", "ground staff", "ground handling", "check-in", "check in agent"],
    "Data Entry / Back Office": ["data entry", "back office", "non-voice", "non voice", "mis executive", "backend process"],
}

_CABIN = re.compile(r"air\s?hostess|cabin crew|flight attendant|steward|in-?flight", re.I)
_AIRPORT = re.compile(r"ground staff|airport|check-?in (agent|executive|staff)|boarding|ground handling|passenger service", re.I)
_HOTEL = re.compile(r"hotel|hospitality|front desk|front office|housekeeping|receptionist|waiter|f&b|food and beverage|restaurant|resort|concierge|guest", re.I)


def category(role: str, jd: str = "") -> str:
    """Which role pool fits. Role text decides first, then the job description. Default: BPO / customer support."""
    for text in (role or "", (jd or "")[:1500]):
        if _CABIN.search(text):
            return "cabin"
        if _AIRPORT.search(text):
            return "airport"
        if _HOTEL.search(text):
            return "hotel"
    return "bpo"


def _ref(o: dict) -> str:
    return o["ref"] or ("Guidance: " + o["tip"] if o["tip"] else "")


def _public(o: dict) -> dict:
    return {"type": o["t"], "question": o["q"], "ref": _ref(o), "tip": o["tip"], "basic": True}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _pool(cat: str):
    role = [o for o in DATA if o["cat"] == cat and o["iv"] and _ref(o)]
    gen = [o for o in DATA if o["cat"] == "general" and o["iv"] and o["ref"]]
    return role, gen


def pick(count: int, role: str = "", jd: str = "", rng: random.Random | None = None) -> list[dict]:
    """Always: 'Tell me about yourself' first, then why-this-job, then a mix of role and general questions from the set."""
    rng = rng or random.Random()
    cat = category(role, jd)
    role_pool, gen_pool = _pool(cat)
    intro = next(o for o in DATA if o["id"] == "A1")
    why = next(o for o in role_pool + gen_pool if o.get("why") and o["cat"] in (cat, "general", "bpo"))
    used = {intro["id"], why["id"]}
    seen = {_norm(intro["q"]), _norm(why["q"])}

    def take(pool, k):
        items = [o for o in pool if o["id"] not in used and _norm(o["q"]) not in seen]
        rng.shuffle(items)
        out = []
        for o in items:
            if len(out) >= k:
                break
            if _norm(o["q"]) in seen:
                continue
            seen.add(_norm(o["q"]))
            used.add(o["id"])
            out.append(o)
        return out

    rest = max(0, count - 2)
    k_role = (rest + 1) // 2
    chosen = take(role_pool, k_role)
    chosen += take(gen_pool, rest - len(chosen))
    if len(chosen) < rest:  # tiny pools: fill from the BPO pool
        chosen += take(_pool("bpo")[0], rest - len(chosen))
    rng.shuffle(chosen)
    return [_public(o) for o in [intro, why, *chosen]][:count]


# ---------- Question Bank roles ----------
def _hint(o: dict) -> str:
    parts = []
    if o["ref"]:
        parts.append(("Sample answer: " if not o["ref"].startswith("Guidance") else "") + o["ref"].replace("Guidance: ", ""))
    if o["tip"] and o["ref"] and not o["ref"].startswith("Guidance"):
        parts.append("Tip: " + o["tip"])
    if o["hi"]:
        parts.append("Hindi: " + o["hi"])
    return " ".join(parts)[:1800]


def bank_roles() -> dict[str, list[tuple]]:
    general = [o for o in DATA if o["cat"] == "general"]
    out = {}
    for cat, name in ROLE_NAMES.items():
        rows = [o for o in DATA if o["cat"] == cat]
        if cat == "bpo":
            rows += [o for o in DATA if o["cat"] == "exp"]
        rows += general
        seen, res = set(), []
        for o in rows:
            if _norm(o["q"]) in seen:
                continue
            seen.add(_norm(o["q"]))
            res.append((o["t"], o["lv"], o["q"], _hint(o)))
        out[name] = res
    return out
