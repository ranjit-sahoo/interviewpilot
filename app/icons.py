"""App icons drawn at startup with the product monogram, so the logo text lives in one place."""
import io
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(__file__), "static", "fonts", "DejaVuSans-Bold.ttf")
MONOGRAM = "MR"
# name -> (pixel size, green square start, green square end as a fraction of the canvas)
ICONS = {
    "icon-192": (192, 0.10, 0.90),
    "icon-512": (512, 0.10, 0.90),
    "apple-touch-icon": (180, 0.10, 0.90),
    "maskable-512": (512, 0.20, 0.80),  # extra margin so Android can crop it into any shape
}


@lru_cache(maxsize=None)
def render(name: str) -> bytes | None:
    spec = ICONS.get(name)
    if not spec:
        return None
    size, lo, hi = spec
    k = 4
    s = size * k
    im = Image.new("RGB", (s, s), (15, 20, 32))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([lo * s, lo * s, hi * s, hi * s], radius=0.17 * (hi - lo) / 0.8 * s, fill=(118, 185, 0))
    d.text((s / 2, s / 2), MONOGRAM, font=ImageFont.truetype(FONT, int((hi - lo) * s * 0.50)), fill=(11, 18, 0), anchor="mm")
    out = io.BytesIO()
    im.resize((size, size), Image.LANCZOS).save(out, "PNG", optimize=True)
    return out.getvalue()
