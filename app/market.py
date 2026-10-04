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
