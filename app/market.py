"""Market (country) context and a cheap offline country detector."""
import re

COUNTRIES = ("US", "India", "Other")

CONTEXT = {
    "US": (
        "MARKET: United States. Interview style: direct, behavioral (STAR), US-client communication norms, "
        "work-authorization awareness (H1B/OPT/GC/USC), time-zone coordination. Salaries in USD per year "
        "(and hourly C2C/W2 rates for contractors)."
    ),
    "India": (
        "MARKET: India. Interview style: strong fundamentals and DSA/system basics, project deep-dives, notice-period "
        "and CTC discussion, service vs product company differences, readiness for US-client calls and time-zone overlap. "
        "Salaries in INR as LPA (lakhs per annum), fixed vs variable."
    ),
    "Other": (
        "MARKET: International / unspecified. Use globally neutral interview practice and state salary figures in "
        "the most plausible local currency, noting uncertainty."
    ),
}


def normalize(country: str | None) -> str:
    c = (country or "").strip().lower()
    if c in ("us", "usa", "united states", "u.s."):
        return "US"
    if c in ("india", "in", "ind"):
        return "India"
    return "Other"


def context(country: str | None) -> str:
    return CONTEXT[normalize(country)]


_IN = re.compile(
    r"\+91|\b(india|bengaluru|bangalore|hyderabad|pune|chennai|mumbai|delhi|noida|gurgaon|gurugram|kolkata|"
    r"bhubaneswar|odisha|karnataka|telangana|maharashtra|tamil nadu|pvt\.? ltd|private limited|lpa|ctc|"
    r"b\.?tech|b\.?e\b|m\.?c\.?a\b|tcs|infosys|wipro|cognizant|hcl|tech mahindra|capgemini)\b",
    re.I,
)
_US = re.compile(
    r"\+1[\s\-(]|\b(usa|united states|h-?1b|opt\b|cpt\b|green card|us citizen|gc[\s-]?ead|w-?2|c2c|1099|"
    r"texas|california|new jersey|new york|virginia|georgia|illinois|florida|north carolina|washington|"
    r"dallas|houston|austin|atlanta|chicago|seattle|charlotte|boston|inc\.|llc)\b",
    re.I,
)


def detect_heuristic(resume: str, jd: str = "") -> dict:
    text = f"{resume}\n{jd}"
    i, u = len(_IN.findall(text)), len(_US.findall(text))
    if i == u == 0:
        return {"country": "Other", "confidence": "low", "reason": "No clear location signals found."}
    country = "India" if i > u else "US"
    gap = abs(i - u)
    conf = "high" if gap >= 3 else "medium" if gap >= 1 else "low"
    if i == u:
        country, conf = "Other", "low"
    return {"country": country, "confidence": conf, "reason": f"Found {i} India and {u} US signals in the text."}


_TECH = re.compile(
    r"\b(developer|engineer|programmer|sdet|devops|sre|software|backend|frontend|full[\s-]?stack|data (engineer|scientist|analyst)|"
    r"machine learning|ml |python|java|javascript|typescript|c\+\+|golang|react|sql|selenium|api|cloud|aws|azure|kubernetes|qa automation)\b",
    re.I,
)


def looks_technical(role: str, resume: str) -> bool:
    """Cheap check so the coding-question call only runs for technical profiles."""
    return bool(_TECH.search(role or "")) or len(_TECH.findall((resume or "")[:6000])) >= 4


# ---------- India basic level (10th / 12th / any graduate, non-engineering) ----------
BASIC_IN = (
    "MARKET: India, entry level (10th/12th pass or any graduate, non-professional). Interview style: simple everyday English, "
    "HR basics, customer handling, shifts and attitude. No coding, no DSA, no system design, no US-client or notice-period assumptions. "
    "Be encouraging. Judge the candidate's English wording and grammar kindly and give simple corrections."
)

_HIGHER = re.compile(
    r"b\.\s?tech|btech|b\.\s?e\b|bachelor of (engineering|technology)|m\.?\s?tech|mtech|\bmca\b|\bmba\b|pgdm|master of|"
    r"m\.\s?sc|m\.\s?com|post[\s-]?graduat|ph\.?d|engineering",
    re.I,
)
_BASIC_EDU = re.compile(
    r"\b(10th|12th|xth|xiith|xii|ssc|hsc|matric|intermediate|higher secondary|secondary school|plus two|\+2)\b|"
    r"class\s?(10|12|x|xii)\b|b\.\s?a\b|bachelor of|b\.\s?com|bcom|b\.\s?sc|bsc|bba|bca|bbm|bhm|b\.\s?voc|graduat|diploma|hons|honou?rs",
    re.I,
)
_COMPUTER_DEGREE = re.compile(r"\bbca\b|b\.\s?sc|bsc|computer", re.I)


def is_basic_in(country, resume: str, role: str = "", level: str = "auto") -> bool:
    """India only. True when the candidate chose Basic, or the resume shows 10th/12th/any graduation (not engineering/PG)
    and the target role is not a technical one for a computer degree. The US and Other markets always return False."""
    if normalize(country) != "India":
        return False
    if (level or "auto") == "basic":
        return True
    if (level or "auto") not in ("auto", "fresher"):
        return False
    text = (resume or "")[:6000]
    if len(text.strip()) < 30 or _HIGHER.search(text) or not _BASIC_EDU.search(text):
        return False
    if looks_technical(role, "") and _COMPUTER_DEGREE.search(text):
        return False
    return True
