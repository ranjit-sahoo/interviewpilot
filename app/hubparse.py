"""Rule-based resume parsing, ranking and duplicate detection. Pure code: no AI, no network, no cost."""
import re

SKILLS = """python java javascript typescript c++ c# php ruby golang kotlin swift sql mysql postgresql mongodb oracle react angular vue node.js django flask spring
html css aws azure gcp docker kubernetes jenkins git linux selenium postman jira testing automation manual-testing api rest devops machine-learning data-analysis
excel power-bi tableau tally gst accounting payroll data-entry typing ms-office word powerpoint outlook sap erp crm salesforce zendesk
customer-service customer-support voice-process non-voice chat-support email-support call-handling telecalling cold-calling lead-generation sales negotiation
communication english hindi arabic tamil telugu kannada malayalam bengali marathi gujarati punjabi
hospitality front-desk front-office housekeeping reservations guest-relations food-beverage cabin-crew ground-handling check-in ticketing
driving heavy-vehicle light-vehicle forklift logistics warehouse inventory dispatch route-planning
recruitment sourcing screening onboarding hr-operations team-handling leadership training quality-analysis escalation complaint-handling""".split()
_ALIASES = {"ms office": "ms-office", "microsoft office": "ms-office", "power bi": "power-bi", "node js": "node.js", "nodejs": "node.js", "front desk": "front-desk",
            "front office": "front-office", "customer service": "customer-service", "customer support": "customer-support", "call handling": "call-handling",
            "data entry": "data-entry", "voice process": "voice-process", "non voice": "non-voice", "cold calling": "cold-calling", "chat support": "chat-support",
            "email support": "email-support", "machine learning": "machine-learning", "manual testing": "manual-testing", "data analysis": "data-analysis",
            "guest relations": "guest-relations", "food and beverage": "food-beverage", "f&b": "food-beverage", "cabin crew": "cabin-crew", "air hostess": "cabin-crew",
            "ground handling": "ground-handling", "heavy vehicle": "heavy-vehicle", "light vehicle": "light-vehicle", "route planning": "route-planning",
            "lead generation": "lead-generation", "team handling": "team-handling", "hr operations": "hr-operations", "quality analysis": "quality-analysis",
            "complaint handling": "complaint-handling", "telecaller": "telecalling", "tele calling": "telecalling", "js": "javascript", "golang": "golang"}
CITIES = """mumbai delhi bengaluru bangalore hyderabad chennai kolkata pune ahmedabad jaipur lucknow noida gurgaon gurugram chandigarh indore bhopal nagpur kochi
coimbatore visakhapatnam patna bhubaneswar cuttack ranchi guwahati thiruvananthapuram mysuru surat vadodara dubai abu-dhabi sharjah ajman ras-al-khaimah fujairah
doha riyadh muscat kuwait manama""".split()
EDU = [("phd", r"\bph\.?d\b"), ("postgraduate", r"\b(m\.?tech|m\.?sc|m\.?com|mba|mca|m\.?a\b|post[- ]?graduate|pgdm)"),
       ("graduate", r"\b(b\.?tech|b\.?e\b|b\.?sc|b\.?com|bba|bca|b\.?a\b|graduat|bachelor)"), ("diploma", r"\b(diploma|iti|polytechnic)\b"),
       ("12th", r"\b(12th|xii|hsc|intermediate|higher secondary|plus two|\+2)\b"), ("10th", r"\b(10th|x\b|ssc|matric|secondary school)")]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+?(?:91|971)[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)|(?<!\d)(?:\+?971[\s-]?)?5\d[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
YEARS = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", re.I)
RANGE = re.compile(r"((?:19|20)\d{2})\s*(?:-|to|–)\s*((?:19|20)\d{2}|present|current|till date|now)", re.I)
NOTICE = re.compile(r"notice period[^\n.]{0,30}?(immediate|\d{1,3}\s*(?:days?|weeks?|months?))", re.I)


def _norm(t: str) -> str:
    t = (t or "").lower()
    for k, v in _ALIASES.items():
        t = t.replace(k, v)
    return t


def skills_in(text: str) -> list[str]:
    t = _norm(text)
    found = []
    for s in SKILLS:
        if re.search(r"(?<![a-z0-9+#.-])" + re.escape(s) + r"(?![a-z0-9+#-])", t):
            found.append(s)
    return found


def parse(text: str, fallback_name: str = "") -> dict:
    text = (text or "")[:60000]
    low = text.lower()
    emails = EMAIL.findall(text)
    phones = [re.sub(r"[^\d+]", "", p) for p in PHONE.findall(text)]
    name = fallback_name.strip()
    if not name:
        for line in text.splitlines()[:6]:
            ln = line.strip()
            if 2 <= len(ln) <= 40 and not EMAIL.search(ln) and not re.search(r"\d", ln) and not re.search(r"resume|curriculum|cv\b", ln, re.I):
                name = ln.title()
                break
    yrs = [float(m.group(1)) for m in YEARS.finditer(text)]
    yrs = [y for y in yrs if y <= 40]
    span = 0.0
    for m in RANGE.finditer(text):
        a = int(m.group(1)); b = m.group(2).lower()
        b = 2026 if not b.isdigit() else int(b)
        if 0 < b - a <= 40:
            span += b - a
    years = max(yrs) if yrs else min(span, 40.0)
    edu = next((k for k, rx in EDU if re.search(rx, low)), "")
    city = next((c.replace("-", " ").title() for c in CITIES if re.search(r"(?<![a-z])" + c.replace("-", "[ -]") + r"(?![a-z])", low)), "")
    n = NOTICE.search(text)
    return {"name": name or "Unnamed", "email": emails[0].lower() if emails else "", "phone": phones[0] if phones else "", "skills": skills_in(text),
            "years": round(years, 1), "education": edu, "city": city, "notice": n.group(1).lower() if n else ""}


def _shingles(text: str, k: int = 5) -> set:
    w = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def _split(items) -> list[str]:
    out = []
    for s in items or []:
        s = _norm(str(s)).strip().replace(" ", "-")
        if s and s not in out:
            out.append(s[:40])
    return out[:40]


def rank(resumes: list[dict], must=None, nice=None, min_years: float = 0, location: str = "") -> list[dict]:
    must, nice = _split(must), _split(nice)
    loc = (location or "").strip().lower()
    rows = []
    for i, r in enumerate(resumes[:100]):
        p = parse(r.get("text", ""), r.get("name", ""))
        have = set(p["skills"]) | set(skills_in(" ".join(must + nice)) if False else [])
        text = _norm(r.get("text", ""))
        hit_must = [s for s in must if s in have or s.replace("-", " ") in text or s in text]
        hit_nice = [s for s in nice if s in have or s.replace("-", " ") in text or s in text]
        miss = [s for s in must if s not in hit_must]
        score = 0.0
        score += 60 * (len(hit_must) / len(must) if must else 1)
        score += 15 * (len(hit_nice) / len(nice) if nice else 1)
        score += 15 * (min(p["years"] / min_years, 1) if min_years else 1)
        loc_ok = (not loc) or loc in (p["city"] or "").lower() or loc in text
        score += 10 if loc_ok else 0
        flags = []
        if miss:
            flags.append("Missing: " + ", ".join(miss))
        if min_years and p["years"] < min_years:
            flags.append(f"Experience {p['years']:g} yrs (needs {min_years:g})")
        if not loc_ok:
            flags.append("Location does not match")
        rows.append({**p, "idx": i, "score": round(score), "must_hit": hit_must, "nice_hit": hit_nice, "flags": flags,
                     "knockout": bool(miss) or bool(min_years and p["years"] < min_years), "_sh": _shingles(r.get("text", "")), "duplicate_of": None})
    for i, a in enumerate(rows):
        for b in rows[:i]:
            same_id = (a["email"] and a["email"] == b["email"]) or (a["phone"] and a["phone"] == b["phone"])
            sa, sb = a["_sh"], b["_sh"]
            sim = len(sa & sb) / max(1, len(sa | sb)) if sa and sb else 0
            if same_id or sim >= 0.8:
                a["duplicate_of"] = b["idx"]
                a["flags"].append("Duplicate of #%d (%s)" % (b["idx"] + 1, "same contact" if same_id else "near-identical text"))
                break
    for r in rows:
        r.pop("_sh", None)
    rows.sort(key=lambda r: (r["duplicate_of"] is not None, r["knockout"], -r["score"]))
    return rows
