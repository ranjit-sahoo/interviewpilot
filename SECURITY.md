# Security notes

## Reporting
Found a problem? Open a private security advisory on the GitHub repository or email the maintainer listed on the GitHub profile. Please do not post exploits publicly.

## Secrets and rotation
Secrets live only in Render environment variables (`NEBIUS_API_KEY`, `DATABASE_URL`, optional `CARD_SECRET`). Nothing is in git.
- **Nebius key:** Token Factory console, API keys, create a new key, set it in Render env, redeploy, then delete the old key. Do this immediately if a key is ever exposed.
- **Database password:** Neon console, Roles, reset password, copy the new connection string into Render `DATABASE_URL`, redeploy.
- **Card/share-link secret:** set `CARD_SECRET` to a new random value. Old share links stop working (they are only cosmetic links).
- **GitHub token / Render deploy hook:** regenerate in their dashboards and update where used.
After any rotation, check `/health` and run one mock interview.

## Spend protection (the model account has a card on file)
- The model key is server-side only; the browser never receives it.
- Per-IP per-minute limit, per-IP daily limit on AI calls, sign-up and login limits.
- `app/spend.py` keeps a persistent estimate of money spent (token usage x generous prices) and stops AI calls at `SPEND_DAILY_CAP_USD` (default 3) per day and `SPEND_TOTAL_CAP_USD` (default 20) overall. Non-AI features keep working.
- Plus a global daily call ceiling (`LLM_DAILY_CAP`) and a per-call output cap (`LLM_MAX_TOKENS`).

## Data and backups
- Database: Neon Postgres, encrypted at rest and in transit (TLS). The app connects with a single application role and only runs parameterized queries.
- Backups: Neon keeps point-in-time history (free tier: a short restore window). To restore, open the Neon console, Branches, Restore, pick a time, or create a branch from a past point and switch `DATABASE_URL` to it. For a longer-term copy, run `pg_dump "$DATABASE_URL" > backup.sql` occasionally.
- Passwords: scrypt (N=2^15, r=8, p=3, per-user salt), upgraded automatically at login. Session tokens are random, stored hashed, sent in an HttpOnly, SameSite=Lax, Secure cookie.

## Dependencies
Versions are pinned in `requirements.txt` and scanned with `pip-audit` (no known vulnerabilities at the time of the last audit).
