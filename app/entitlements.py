"""Plan gating. No payments exist yet, so every plan is free and generous. When paid plans launch, change only
PLANS (limits per role) and set users.plan; the checks below already run in every recruiter endpoint."""

PLANS = {
    "free": {"campaigns": 100, "invites_per_campaign": 200, "resumes_per_run": 100, "team_members": 10, "api": True},
    # "pro": {...}  later: raise the numbers, nothing else needs to change.
}


def limit(user: dict, key: str):
    return PLANS.get((user or {}).get("plan") or "free", PLANS["free"]).get(key)


def role_of(user) -> str:
    return (user or {}).get("role") or "guest"
