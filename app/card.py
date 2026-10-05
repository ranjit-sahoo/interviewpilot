"""Shareable score card: a signed, self-contained token (stored nowhere, so links survive restarts) rendered as a PNG and a share page.

The card holds only: score, role, verdict, level, country, up to three strengths, four skill averages, an optional
display name and a date. It never contains resume text."""
import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import time
import zlib
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

FONTS = os.path.join(os.path.dirname(__file__), "static", "fonts")
import hashlib as _hl

_raw = os.environ.get("CARD_SECRET") or os.environ.get("NEBIUS_API_KEY") or secrets.token_hex(16)
_SECRET = _hl.sha256(b"interviewpilot-card-v1:" + _raw.encode()).digest()  # derived, never the raw API key


def verdict(score: float) -> str:
    if score >= 4.2:
        return "Interview-ready"
    if score >= 3.4:
        return "Strong - polish a few answers"
    if score >= 2.6:
        return "Getting there"
    return "Keep practicing"


def _clean(s, n):
    return " ".join(str(s or "").split())[:n]


def make_payload(report: dict, turns: list, role: str, level: str, country: str, name: str = "") -> dict:
    try:
        score = max(0.0, min(5.0, float(report.get("overall_score", 0))))
    except (TypeError, ValueError):
        score = 0.0
    keys = [("clarity", "Clarity"), ("depth", "Depth"), ("correctness", "Accuracy"), ("star", "Structure")]
    skills = []
    for k, label in keys:
        vals = []
        for t in turns:
            try:
                vals.append(float(((t.get("feedback") or {}).get("scores") or {}).get(k)))
            except (TypeError, ValueError):
                pass
        skills.append([label, round(sum(vals) / len(vals), 1) if vals else 0.0])
    strengths = [_clean(x, 70) for x in (report.get("strengths") or []) if _clean(x, 70)][:3]
    return {"s": round(score, 1), "r": _clean(role, 60), "l": level if level in ("auto", "fresher", "experienced", "brutal") else "auto",
            "c": country if country in ("US", "India", "Other") else "Other", "n": _clean(name, 40), "g": strengths,
            "k": skills, "d": time.strftime("%b %Y")}


def sign(payload: dict) -> str:
    raw = zlib.compress(json.dumps(payload, separators=(",", ":")).encode(), 9)
    body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest()[:12]).decode().rstrip("=")
    return f"{body}.{sig}"


def verify(token: str):
    try:
        body, sig = token.rsplit(".", 1)
        good = base64.urlsafe_b64encode(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest()[:12]).decode().rstrip("=")
        if not hmac.compare_digest(sig, good):
            return None
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        d = zlib.decompressobj().decompress(raw, 20000)
        p = json.loads(d)
        return p if isinstance(p, dict) and "s" in p else None
    except Exception:
        return None


def _f(size, bold=False):
    return ImageFont.truetype(os.path.join(FONTS, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)


def _fit(draw, text, font_fn, size, maxw, bold=True):
    while size > 20 * 2 and draw.textlength(text, font=font_fn(size, bold)) > maxw:
        size -= 2
    return font_fn(size, bold)


def render_png(p: dict) -> bytes:
    S = 2  # supersample for smooth edges
    W, H = 1200 * S, 630 * S
    img = Image.new("RGB", (W, H), "#070b1a")
    px = img.load()
    # diagonal gradient background
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            t = (x / W * 0.6 + y / H * 0.4)
            c = (int(9 + 22 * t), int(14 + 30 * t), int(34 + 70 * (1 - abs(t - 0.5) * 2) + 20 * t))
            for dy in (0, 1):
                for dx in (0, 1):
                    if x + dx < W and y + dy < H:
                        px[x + dx, y + dy] = c
    glow = Image.new("RGB", (W, H), "#000000")
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W * 0.55, -H * 0.4, W * 1.2, H * 0.6], fill="#1b3a8a")
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(120 * S))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.55)
    d = ImageDraw.Draw(img)
    f = lambda sz, b=False: _f(sz * S, b)

    # brand
    d.rounded_rectangle([60 * S, 48 * S, 112 * S, 100 * S], radius=14 * S, fill="#4a76ee")
    d.text((86 * S, 75 * S), "MR", font=f(24, True), fill="white", anchor="mm")
    d.text((128 * S, 75 * S), "MockRep", font=f(30, True), fill="#e8edff", anchor="lm")
    tag = {"US": "US market", "India": "India market"}.get(p.get("c"), "Global")
    lvl = {"fresher": "Fresher level", "experienced": "Experienced level", "brutal": "Brutal level"}.get(p.get("l"), "")
    chip = tag + ("  |  " + lvl if lvl else "")
    cw = d.textlength(chip, font=f(20)) + 40 * S
    d.rounded_rectangle([1140 * S - cw, 54 * S, 1140 * S, 96 * S], radius=21 * S, fill="#16224a", outline="#2c3f7a", width=2 * S)
    d.text((1140 * S - cw / 2, 75 * S), chip, font=f(20), fill="#b9c7ff", anchor="mm")

    # score ring
    cx, cy, R = 250 * S, 360 * S, 135 * S
    box = [cx - R, cy - R, cx + R, cy + R]
    d.arc(box, 0, 360, fill="#1a2550", width=26 * S)
    sc = p["s"]
    col = "#37d67a" if sc >= 4.2 else "#5b8cff" if sc >= 3.4 else "#f5b83d" if sc >= 2.6 else "#ff6b6b"
    d.arc(box, -90, -90 + 360 * sc / 5, fill=col, width=26 * S)
    d.text((cx, cy - 8 * S), f"{sc:.1f}", font=f(92, True), fill="white", anchor="mm")
    d.text((cx, cy + 62 * S), "out of 5", font=f(24), fill="#9fb0e6", anchor="mm")

    # right column
    x0 = 470 * S
    who = (p.get("n") + " | ") if p.get("n") else ""
    d.text((x0, 168 * S), (who + "Mock interview result").upper(), font=f(20, True), fill="#7f93d8", anchor="lm")
    role_txt = p.get("r") or "Interview"
    d.text((x0, 226 * S), role_txt, font=_fit(d, role_txt, lambda sz, b: _f(sz, b), 58 * S, 690 * S), fill="white", anchor="lm")
    v = verdict(sc)
    d.text((x0, 292 * S), v, font=_fit(d, v, lambda sz, b: _f(sz, b), 38 * S, 690 * S), fill=col, anchor="lm")

    # skill bars
    y = 342
    for label, val in p.get("k", []):
        d.text((x0, y * S), label, font=f(20), fill="#c5d0f5", anchor="lm")
        bx0, bx1 = x0 + 150 * S, x0 + 560 * S
        d.rounded_rectangle([bx0, (y - 7) * S, bx1, (y + 7) * S], radius=7 * S, fill="#1a2550")
        if val > 0:
            d.rounded_rectangle([bx0, (y - 7) * S, bx0 + (bx1 - bx0) * min(val, 5) / 5, (y + 7) * S], radius=7 * S, fill="#5b8cff")
        d.text((bx1 + 20 * S, y * S), f"{val:.1f}", font=f(20, True), fill="#e8edff", anchor="lm")
        y += 38
    # strengths
    if p.get("g"):
        d.text((x0, 508 * S), "STRENGTHS", font=f(16, True), fill="#7f93d8", anchor="lm")
        sx = x0
        for g in p["g"][:3]:
            g = g if len(g) <= 28 else g[:25] + "..."
            w = d.textlength(g, font=f(17)) + 28 * S
            if sx + w > 1150 * S:
                break
            d.rounded_rectangle([sx, 524 * S, sx + w, 556 * S], radius=17 * S, fill="#14305a", outline="#2a5aa0", width=S)
            d.text((sx + w / 2, 540 * S), g, font=f(17), fill="#d6e4ff", anchor="mm")
            sx += w + 10 * S
    # footer
    d.text((60 * S, 590 * S), "Practice your own AI mock interview - free", font=f(20), fill="#9fb0e6", anchor="lm")
    d.text((1140 * S, 590 * S), (p.get("d") or "") + "  |  mockrep.onrender.com", font=f(18), fill="#6f82c8", anchor="rm")
    img = img.resize((1200, 630), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def page(p: dict, token: str, base: str) -> str:
    e = html.escape
    title = f"{e(p.get('n') or 'A candidate')} scored {p['s']:.1f}/5 in a mock {e(p.get('r') or '')} interview"
    desc = f"{verdict(p['s'])}. Practice your own AI mock interview, free, with MockRep."
    img = f"{base}/c/{token}.png"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:url" content="{base}/c/{token}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{img}">
<style>body{{margin:0;background:#070b1a;color:#e8edff;font-family:system-ui,Arial,sans-serif;text-align:center;padding:24px}}
img{{max-width:100%;width:900px;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.5)}}
a.b{{display:inline-block;margin:22px 0;padding:14px 26px;background:linear-gradient(135deg,#3b66e0,#2c52c4);color:#fff;border-radius:12px;text-decoration:none;font-weight:700}}</style></head>
<body><h1 style="font-size:22px">{title}</h1><img src="{img}" alt="Mock interview score card: {p['s']:.1f} out of 5"><br>
<a class="b" href="{base}/">Try your own free mock interview</a><p style="color:#9fb0e6">MockRep - AI interview coach for India and US candidates &middot; <a href="/privacy" style="color:#9fb0e6">Privacy Policy</a></p></body></html>"""
