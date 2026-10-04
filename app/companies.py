"""Curated interview profiles for well-known US and India employers (instant, no AI call).

These are general, publicly known patterns, not leaked questions. Rounds and focus vary by team and year,
so the UI labels them as typical."""

# name: (country, kind, typical rounds, focus areas, tip)
_C = {
    "Google": ("US", "Product", "Recruiter call, 1-2 phone/online coding rounds, 4-5 onsite rounds (coding, system design, behavioral)", ["Data structures and algorithms", "System design", "Googleyness and leadership"], "Talk through your thinking out loud and state complexity before coding."),
    "Amazon": ("US", "Product", "Online assessment, phone screen, loop of 4-5 interviews with a bar raiser", ["Leadership Principles (STAR stories)", "Coding", "System design for senior roles"], "Prepare 8-10 STAR stories mapped to the Leadership Principles."),
    "Microsoft": ("US", "Product", "Recruiter call, 1-2 technical screens, onsite loop of 3-4 rounds", ["Coding and problem solving", "Design", "Collaboration and growth mindset"], "Show how you learn from feedback and work across teams."),
    "Meta": ("US", "Product", "Recruiter call, technical screen, onsite with coding, system design and behavioral", ["Coding speed and accuracy", "System or product design", "Behavioral: impact and conflict"], "Practice solving two medium problems in 40 minutes."),
    "Apple": ("US", "Product", "Recruiter call, team phone screens, onsite with several team interviews", ["Role-specific depth", "Attention to detail", "Passion for the product"], "Know the team's product and be specific about your own contributions."),
    "Netflix": ("US", "Product", "Recruiter call, hiring manager chat, technical and culture interviews", ["Senior-level depth", "Judgment and ownership", "Culture memo alignment"], "Read the Netflix culture memo and bring real examples of independent decisions."),
    "Deloitte": ("US", "Consulting/IT services", "Recruiter screen, case or technical interview, manager and partner rounds", ["Case thinking", "Client communication", "Technology fundamentals"], "Structure answers clearly and show client-facing communication."),
    "Accenture": ("US", "Consulting/IT services", "Online assessment, technical interview, HR or managerial round", ["Technology basics", "Client scenarios", "Adaptability"], "Expect scenario questions about working with clients and changing requirements."),
    "IBM": ("US", "Enterprise tech", "Online assessment, technical interview, managerial round", ["Core technology skills", "Problem solving", "Teamwork"], "Be ready to explain projects in depth, including your exact role."),
    "Oracle": ("US", "Enterprise tech", "Phone screen, multiple technical rounds, hiring manager round", ["Databases and SQL", "Java or cloud depth", "System design"], "Brush up SQL and database internals."),
    "Salesforce": ("US", "Enterprise tech", "Recruiter call, technical screen, virtual onsite with values and technical rounds", ["Role skills", "Customer focus", "Values: trust and equality"], "Connect your answers to customer success."),
    "Walmart Global Tech": ("US", "Product/retail tech", "Online assessment, technical rounds, design and managerial round", ["Data structures", "System design", "Scale and reliability"], "Think about high-traffic retail systems in design rounds."),
    "JPMorgan Chase": ("US", "Finance", "HireVue or online assessment, technical rounds, Super Day with behavioral", ["Coding and fundamentals", "Behavioral and teamwork", "Risk awareness"], "Prepare concise stories that show ownership and care for quality."),
    "Goldman Sachs": ("US", "Finance", "Online assessment, technical rounds, Super Day", ["Algorithms", "Problem solving under pressure", "Motivation for finance"], "Explain why this firm and be sharp on fundamentals."),
    "Capital One": ("US", "Finance", "Online assessment, power day with case, technical and behavioral", ["Case interview", "Coding", "Behavioral"], "Practice a structured approach to business cases."),
    "Cognizant (US)": ("US", "IT services", "Recruiter screen, technical interview, client or manager round", ["Technical skills", "Client communication", "Work authorization and availability"], "Be clear about your stack, availability and work authorization."),
    "TCS": ("India", "IT services", "Online test (aptitude and coding), technical interview, managerial and HR rounds", ["Core CS fundamentals", "Project explanation", "Willingness to relocate and learn"], "Know your final-year or work project end to end."),
    "Infosys": ("India", "IT services", "Online test, technical interview, HR round", ["Fundamentals (DBMS, OOP, one language)", "Project discussion", "Communication"], "Speak clearly and be strong on basics."),
    "Wipro": ("India", "IT services", "Online assessment, technical round, HR round", ["Programming basics", "Aptitude", "Communication"], "Practice aptitude and a simple coding problem."),
    "HCLTech": ("India", "IT services", "Online test, technical interview, HR round", ["Technology fundamentals", "Project discussion", "Communication"], "Prepare a clear two-minute project walkthrough."),
    "Tech Mahindra": ("India", "IT services", "Online test, technical interview, HR round", ["Basics of your stack", "Problem solving", "Communication"], "Be ready for questions on every skill listed on your resume."),
    "Cognizant (India)": ("India", "IT services", "Online assessment, technical interview, HR round", ["Programming basics", "Project work", "Communication"], "Expect questions on any tool you list. Keep your resume honest."),
    "Capgemini": ("India", "IT services", "Online game-based and technical test, technical interview, HR", ["Fundamentals", "Aptitude and logic", "Communication"], "Practice logical reasoning and a basic coding round."),
    "LTIMindtree": ("India", "IT services", "Online test, technical round, managerial or HR round", ["Core stack", "Project explanation", "Client communication"], "Prepare real examples of delivery under deadlines."),
    "Flipkart": ("India", "Product", "Online coding, 2-3 technical rounds (DSA, machine coding, design), hiring manager", ["Data structures and algorithms", "Machine coding and low-level design", "Scale and system design"], "Practice machine-coding rounds with clean, extensible code."),
    "Swiggy": ("India", "Product", "Coding round, technical rounds, design and hiring manager", ["DSA", "System design", "Ownership and speed"], "Show how you ship and own outcomes."),
    "Zomato": ("India", "Product", "Coding or take-home, technical rounds, hiring manager", ["DSA", "Design", "Product thinking"], "Think about reliability and real-time order flows."),
    "Paytm": ("India", "Fintech", "Coding round, technical rounds, managerial round", ["DSA", "Backend design", "Payments basics"], "Know basics of payments, idempotency and consistency."),
    "PhonePe": ("India", "Fintech", "Coding, technical deep-dives, design, hiring manager", ["DSA", "System design at scale", "Reliability"], "Prepare for deep questions about your past systems."),
    "Razorpay": ("India", "Fintech", "Coding or machine round, technical rounds, culture round", ["Problem solving", "API and system design", "Ownership"], "Show product sense for developer-facing payments."),
    "Zoho": ("India", "Product", "Written rounds, programming rounds, technical and HR", ["Programming logic without frameworks", "Problem solving", "Fundamentals"], "Practice writing clean code from scratch without libraries."),
    "Freshworks": ("India", "Product/SaaS", "Coding round, technical rounds, managerial", ["DSA", "Design", "Customer focus"], "Prepare examples of building features end to end."),
    "Ola": ("India", "Product", "Coding round, technical rounds, design", ["DSA", "System design", "Speed of execution"], "Think about location and real-time systems."),
    "HDFC Bank": ("India", "Banking", "Group or aptitude round, technical or domain interview, HR", ["Domain and banking basics", "Technology skills", "Communication"], "Learn the basics of banking products and compliance."),
}

_ALIASES = {"google": "Google", "alphabet": "Google", "amazon": "Amazon", "aws": "Amazon", "microsoft": "Microsoft", "meta": "Meta",
            "facebook": "Meta", "apple": "Apple", "netflix": "Netflix", "deloitte": "Deloitte", "accenture": "Accenture", "ibm": "IBM",
            "oracle": "Oracle", "salesforce": "Salesforce", "walmart": "Walmart Global Tech", "jpmorgan": "JPMorgan Chase",
            "jp morgan": "JPMorgan Chase", "chase": "JPMorgan Chase", "goldman": "Goldman Sachs", "capital one": "Capital One",
            "tcs": "TCS", "tata consultancy": "TCS", "infosys": "Infosys", "wipro": "Wipro", "hcl": "HCLTech", "tech mahindra": "Tech Mahindra",
            "capgemini": "Capgemini", "ltimindtree": "LTIMindtree", "mindtree": "LTIMindtree", "lti": "LTIMindtree", "flipkart": "Flipkart",
            "swiggy": "Swiggy", "zomato": "Zomato", "paytm": "Paytm", "phonepe": "PhonePe", "razorpay": "Razorpay", "zoho": "Zoho",
            "freshworks": "Freshworks", "ola": "Ola", "hdfc": "HDFC Bank"}


def names() -> list[str]:
    return sorted(_C)


def find(company: str, country: str | None = None) -> dict | None:
    t = " ".join((company or "").lower().split())
    if not t:
        return None
    name = next((n for n in _C if n.lower() == t), None)
    if not name:
        if t == "cognizant":
            name = "Cognizant (India)" if (country or "").lower().startswith("in") else "Cognizant (US)"
        else:
            name = next((v for k, v in _ALIASES.items() if t == k or (len(k) > 3 and k in t)), None)
    if not name:
        return None
    c, kind, rounds, focus, tip = _C[name]
    return {"name": name, "country": c, "kind": kind, "rounds": rounds, "focus": focus, "tip": tip,
            "note": "Typical pattern from public information. Rounds vary by team and year."}
